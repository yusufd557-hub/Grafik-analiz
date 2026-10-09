"""Strateji tanımı, değerlendirme, ileri bakış denetimi ve geçme şartları.

Bir strateji `StrategySpec` ile tanımlanır. `signal_fn` her bacak için hedef
pozisyon serisi döndürür:

    def signal_fn(data, funding, **params) -> dict[(piyasa, coin), pd.Series]

`data[(piyasa, coin)]` kapanmış mumlar (DataFrame), `funding[coin]` vadeli
fonlama oranlarıdır. t barındaki değer, t barının kapanışında karar verilen
hedef pozisyondur; işlem t+1 açılışında yapılır (bkz. `backtest`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..data import FUTURES
from . import ledger
from .backtest import LegResult, backtest_leg, combine
from .data import load, load_funding
from .metrics import alpha_beta, daily_returns, summarize, window as cut_window
from .protocol import (
    BENCHMARK_SYMBOLS,
    REQUIRE_ALPHA,
    HOLDOUT_CONFIDENCE,
    MIN_SHARPE_VALID,
    MIN_TRADES_HOLDOUT,
    MIN_TRADES_VALID,
    PERIODS,
    STRESS_MULTIPLIER,
)

Leg = tuple[str, str]


@dataclass
class StrategySpec:
    name: str
    family: str
    interval: str
    legs: tuple[Leg, ...]
    signal_fn: Callable[..., dict]
    params: dict = field(default_factory=dict)
    weights: dict | None = None
    """Bacak başına sermaye payı. Verilmezse eşit (toplam 1)."""
    description: str = ""

    def leg_weights(self) -> dict:
        if self.weights is not None:
            return dict(self.weights)
        return {leg: 1.0 / len(self.legs) for leg in self.legs}


@dataclass
class RunResult:
    spec: StrategySpec
    legs: dict
    returns: pd.Series
    trades: pd.DataFrame
    exposure: pd.Series
    costs: pd.Series
    funding: pd.Series


def load_data(spec: StrategySpec, scope: str = "dev") -> tuple[dict, dict]:
    data = {leg: load(leg[1], spec.interval, leg[0], scope) for leg in spec.legs}
    funding = {leg[1]: load_funding(leg[1], scope) for leg in spec.legs if leg[0] == FUTURES}
    return data, funding


def compute_signals(spec: StrategySpec, data: dict, funding: dict) -> dict:
    signals = spec.signal_fn(data, funding, **spec.params)
    missing = [leg for leg in spec.legs if leg not in signals]
    if missing:
        raise ValueError(f"{spec.name}: sinyal üretilmeyen bacaklar: {missing}")
    return signals


def backtest(spec: StrategySpec, data: dict, funding: dict, signals: dict, cost_multiplier: float = 1.0) -> RunResult:
    weights = spec.leg_weights()
    legs: dict[Leg, LegResult] = {}
    for leg in spec.legs:
        market, symbol = leg
        legs[leg] = backtest_leg(
            data[leg],
            signals[leg],
            market=market,
            symbol=symbol,
            funding=funding.get(symbol) if market == FUTURES else None,
            cost_multiplier=cost_multiplier,
        )
    returns = combine(legs, weights)
    index = returns.index

    def weighted(attr: str) -> pd.Series:
        total = pd.Series(0.0, index=index)
        for leg, res in legs.items():
            total = total.add(weights[leg] * getattr(res, attr).reindex(index).fillna(0.0), fill_value=0.0)
        return total

    exposure = pd.Series(0.0, index=index)
    for leg, res in legs.items():
        exposure = exposure.add(weights[leg] * res.position.abs().reindex(index).fillna(0.0), fill_value=0.0)

    frames = []
    for leg, res in legs.items():
        if res.trades.empty:
            continue
        t = res.trades.copy()
        t["leg"] = f"{leg[0]}:{leg[1]}"
        # Portföy düzeyinde katkı: bacağın sermaye payı ile ölçeklenir.
        t["net_return"] = t["net_return"] * weights[leg]
        t["gross_return"] = t["gross_return"] * weights[leg]
        frames.append(t)
    trades = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["entry_time", "exit_time", "direction", "bars", "size", "gross_return", "net_return", "leg"]
    )
    return RunResult(spec, legs, returns, trades, exposure, weighted("cost"), weighted("funding"))


def run(spec: StrategySpec, scope: str = "dev", cost_multiplier: float = 1.0) -> RunResult:
    data, funding = load_data(spec, scope)
    return backtest(spec, data, funding, compute_signals(spec, data, funding), cost_multiplier)


def benchmark_daily(spec: StrategySpec, scope: str = "dev") -> pd.Series:
    """Piyasa kıyası: BTC/ETH/SOL eşit ağırlıklı al-tut günlük getirisi (stratejinin piyasasında).

    Stratejinin herhangi bir bacağı vadeliyse vadeli, değilse spot fiyatlar kullanılır.
    Henüz listelenmemiş coin o günlerde ortalamaya girmez.
    """
    market = FUTURES if any(m == FUTURES for m, _ in spec.legs) else "spot"
    columns = []
    for sym in BENCHMARK_SYMBOLS:
        try:
            df = load(sym, "1d", market, scope)
        except FileNotFoundError:
            continue
        o = df["open"].astype(float)
        r = o.shift(-1) / o - 1.0
        if len(r):
            r.iloc[-1] = float(df["close"].iloc[-1]) / float(o.iloc[-1]) - 1.0
        r.index = r.index.floor("1D")
        columns.append(r.rename(sym))
    if not columns:
        return pd.Series(dtype=float)
    return pd.concat(columns, axis=1).mean(axis=1)


def _scope_for(window: str) -> str:
    return "holdout" if window == "holdout" else "dev"


def evaluate(
    spec: StrategySpec,
    windows: tuple[str, ...] = ("dev_train", "dev_valid"),
    cost_multipliers: tuple[float, ...] = (1.0, STRESS_MULTIPLIER),
    record: bool = True,
    confidence: float = 0.95,
) -> dict:
    """Pencere × maliyet katı için ölçüler. Her değerlendirme deney defterine yazılır."""
    out: dict = {}
    by_scope: dict[str, list[str]] = {}
    for w in windows:
        by_scope.setdefault(_scope_for(w), []).append(w)
    for scope, wins in by_scope.items():
        data, funding = load_data(spec, scope)
        signals = compute_signals(spec, data, funding)
        bench = benchmark_daily(spec, scope)
        for mult in cost_multipliers:
            result = backtest(spec, data, funding, signals, mult)
            for w in wins:
                start, end = PERIODS[w]
                metrics = summarize(
                    result.returns,
                    result.trades,
                    result.exposure,
                    result.costs,
                    result.funding,
                    start,
                    end,
                    confidence=confidence,
                )
                if not bench.empty:
                    metrics.update(alpha_beta(daily_returns(cut_window(result.returns, start, end)), bench))
                out.setdefault(w, {})[mult] = metrics
                if record:
                    ledger.record(spec.family, spec.name, {"interval": spec.interval, "legs": [list(l) for l in spec.legs], **spec.params}, w, mult, metrics)
    return out


def assert_causal(
    spec: StrategySpec,
    fractions: tuple[float, ...] = (0.55, 0.8, 0.97),
    atol: float = 1e-9,
) -> None:
    """Seri kısaltılınca geçmiş sinyaller değişiyorsa strateji geleceği görüyordur."""
    data, funding = load_data(spec, "dev")
    full = compute_signals(spec, data, funding)
    first_leg = spec.legs[0]
    index = data[first_leg].index
    for frac in fractions:
        cut = index[int(len(index) * frac)]
        part_data = {leg: frame[frame.index <= cut] for leg, frame in data.items()}
        part_funding = {sym: f[f.index <= cut] for sym, f in funding.items()}
        part = compute_signals(spec, part_data, part_funding)
        for leg in spec.legs:
            fa, fb = _as_frame(full[leg]), _as_frame(part[leg])
            for col in fa.columns:
                a = fa[col].astype(float).reindex(part_data[leg].index)
                b = fb[col].astype(float).reindex(part_data[leg].index) if col in fb else pd.Series(np.nan, index=a.index)
                both_nan = a.isna() & b.isna()
                diff = (a - b).abs().where(~both_nan, 0.0).fillna(np.inf)
                if (diff > atol).any():
                    bad = diff[diff > atol].index[0]
                    raise AssertionError(
                        f"{spec.name}: {leg} sinyali ({col}) {bad} tarihinde seri {cut} noktasında kesilince değişiyor "
                        f"(tam: {a.loc[bad]}, kesik: {b.loc[bad]}) — ileri bakış var"
                    )


def _as_frame(signal) -> pd.DataFrame:
    if isinstance(signal, pd.DataFrame):
        return signal
    return pd.Series(signal, dtype=float).to_frame("target")


def candidate_check(results: dict) -> dict:
    """Geliştirme aşaması aday şartları (ön kayıtlı)."""
    v1 = results["dev_valid"][1.0]
    v2 = results["dev_valid"][STRESS_MULTIPLIER]
    t1 = results.get("dev_train", {}).get(1.0, {})
    checks = {
        "gelistirme_egitim_net_pozitif": t1.get("total_return", -1) > 0,
        "dogrulama_net_pozitif": v1.get("total_return", -1) > 0,
        "dogrulama_2x_maliyette_net_pozitif": v2.get("total_return", -1) > 0,
        "dogrulama_sharpe_yeterli": (v1.get("sharpe") or -9) >= MIN_SHARPE_VALID,
        "dogrulama_islem_sayisi": v1.get("trades", 0) >= MIN_TRADES_VALID,
    }
    if REQUIRE_ALPHA:
        # Sürüm 2: kâr piyasanın yönünden değil stratejiden gelmeli.
        checks["egitim_alfa_pozitif"] = (t1.get("alfa") or -1) > 0
        checks["dogrulama_alfa_pozitif"] = (v1.get("alfa") or -1) > 0
    checks["aday"] = all(checks.values())
    return checks


def holdout_check(results: dict, n_finalists: int) -> dict:
    """Görülmemiş dönem şartları (ön kayıtlı). Seviye 1: kârlı; Seviye 2: istatistiksel."""
    h1 = results["holdout"][1.0]
    h2 = results["holdout"][STRESS_MULTIPLIER]
    level1 = {
        "net_pozitif": h1.get("total_return", -1) > 0,
        "2x_maliyette_net_pozitif": h2.get("total_return", -1) > 0,
        "islem_sayisi": h1.get("trades", 0) >= MIN_TRADES_HOLDOUT,
        "en_iyi_islem_cikinca_pozitif": (h1.get("total_without_best") or -1) > 0,
    }
    alpha = (1 - HOLDOUT_CONFIDENCE) / max(1, n_finalists)
    level2 = {"bootstrap_p_degeri": h1.get("p_value", 1.0) < alpha, "esik": alpha}
    return {
        "seviye1": level1,
        "seviye1_gecti": all(level1.values()),
        "seviye2": level2,
        "seviye2_gecti": all(level1.values()) and level2["bootstrap_p_degeri"],
    }
