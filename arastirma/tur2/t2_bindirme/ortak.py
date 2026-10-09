"""t2_bindirme araştırma yardımcıları (yalnız protokol sürüm 2, yalnız eğitim dönemi).

- `degerlendir(spec)`: `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`
  (deftere yazılır) + `alt_donem(spec)` ölçüleri, tek satır.
- `egitim_calistir(spec)`: veri ve fonlama 31.12.2024 sonunda (DEV_TRAIN_END öncesi)
  KESİLDİKTEN sonra sinyal ve backtest. dev_valid verisi hiç yüklenmez/kullanılmaz.
- `alt_donem(spec)`: eğitim içi alt dönem ölçüleri (2020–2023 ve 2024 alfası, yıllık getiriler,
  2020+ Sharpe/oynaklık). Yalnız deftere yazılmış yapılandırmalar için çağrılır.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.data import load
from grafik_analiz.research.evaluate import backtest, compute_signals, evaluate, load_data
from grafik_analiz.research.metrics import alpha_beta, daily_returns

assert protocol.PROTOCOL_VERSION == "2", "GRAFIK_ANALIZ_PROTOKOL=2 gerekli"
TRAIN_END = protocol.DEV_TRAIN_END
T2020 = pd.Timestamp("2020-01-01", tz="UTC")
T2024 = pd.Timestamp("2024-01-01", tz="UTC")
KLASOR = Path(__file__).resolve().parent


def egitim_verisi(spec):
    data, funding = load_data(spec, "dev")
    data = {leg: df[df["close_time"] < TRAIN_END].copy() for leg, df in data.items()}
    funding = {s: f[f.index < TRAIN_END].copy() for s, f in funding.items()}
    return data, funding


def egitim_calistir(spec, mult: float = 1.0, data_funding=None):
    data, funding = data_funding or egitim_verisi(spec)
    signals = compute_signals(spec, data, funding)
    return backtest(spec, data, funding, signals, mult), signals


def kiyas_egitim(market: str) -> pd.Series:
    """BTC/ETH/SOL eşit ağırlıklı al-tut günlük getirisi (evaluate.benchmark_daily ile aynı tarif), eğitimde kesik."""
    cols = []
    for sym in protocol.BENCHMARK_SYMBOLS:
        df = load(sym, "1d", market, "dev")
        df = df[df["close_time"] < TRAIN_END]
        o = df["open"].astype(float)
        r = o.shift(-1) / o - 1.0
        if len(r):
            r.iloc[-1] = float(df["close"].iloc[-1]) / float(o.iloc[-1]) - 1.0
        r.index = r.index.floor("1D")
        cols.append(r.rename(sym))
    return pd.concat(cols, axis=1).mean(axis=1)


_KIYAS: dict = {}


def kiyas(market: str) -> pd.Series:
    if market not in _KIYAS:
        _KIYAS[market] = kiyas_egitim(market)
    return _KIYAS[market]


def _market(spec) -> str:
    return "futures" if any(m == "futures" for m, _ in spec.legs) else "spot"


def _ab(d: pd.Series, b: pd.Series, a, z) -> dict:
    dd = d[(d.index >= a) & (d.index < z)]
    return alpha_beta(dd, b)


def alt_donem(spec, res=None) -> dict:
    if res is None:
        res, _ = egitim_calistir(spec)
    d = daily_returns(res.returns)
    b = kiyas(_market(spec))
    out = {}
    a1 = _ab(d, b, T2020, T2024)
    a2 = _ab(d, b, T2024, TRAIN_END)
    a0 = _ab(d, b, T2020, TRAIN_END)
    out["alfa_20_23"] = a1["alfa"]
    out["beta_20_23"] = a1["beta"]
    out["alfa_24"] = a2["alfa"]
    out["beta_24"] = a2["beta"]
    out["alfa_20p"] = a0["alfa"]
    out["alfa_t_20p"] = a0["alfa_t"]
    d20 = d[d.index >= T2020]
    out["sharpe_20p"] = float(d20.mean() / d20.std() * math.sqrt(365)) if d20.std() > 0 else float("nan")
    out["vol_20p"] = float(d20.std() * math.sqrt(365))
    for y in range(2020, 2025):
        dy = d[(d.index >= pd.Timestamp(f"{y}-01-01", tz="UTC")) & (d.index < pd.Timestamp(f"{y + 1}-01-01", tz="UTC"))]
        out[f"r{y}"] = float((1 + dy).prod() - 1) if len(dy) else float("nan")
    t = res.trades
    t20 = t[t["entry_time"] >= T2020] if len(t) else t
    out["islem_yil_20p"] = float(len(t20) / ((TRAIN_END - T2020).days / 365.25))
    ex = res.exposure[res.exposure.index >= T2020]
    out["ort_maruz"] = float(ex.mean()) if len(ex) else float("nan")
    out["fonlama_20p"] = float(res.funding[res.funding.index >= T2020].sum())
    out["maliyet_20p"] = float(res.costs[res.costs.index >= T2020].sum())
    return out


def degerlendir(spec, mults=(1.0, 2.0), alt: bool = True) -> dict:
    t0 = time.time()
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=mults)
    m1 = res["dev_train"][1.0]
    row = {
        "ad": spec.name,
        "ret": m1.get("total_return"),
        "sharpe": m1.get("sharpe"),
        "mdd": m1.get("max_drawdown"),
        "trades": m1.get("trades"),
        "alfa": m1.get("alfa"),
        "beta": m1.get("beta"),
        "alfa_t": m1.get("alfa_t"),
        "maruz": m1.get("exposure"),
        "maliyet": m1.get("total_costs"),
        "fonlama": m1.get("total_funding"),
    }
    if 2.0 in res["dev_train"]:
        m2 = res["dev_train"][2.0]
        row["ret2"] = m2.get("total_return")
        row["sharpe2"] = m2.get("sharpe")
        row["alfa2"] = m2.get("alfa")
    if alt:
        row.update(alt_donem(spec))
    row["sure"] = round(time.time() - t0, 1)
    return row


def yaz(rows: list[dict], path: Path) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def log(msg: str) -> None:
    print(msg, flush=True)
    sys.stdout.flush()
