"""Ortak yardımcılar: yalnız dev_train verisi (2024-01-01 öncesi) ile betimsel analiz.

Veri `grafik_analiz.research.load(..., scope="dev")` ile yüklenir ve HEMEN
DEV_TRAIN_END öncesine kesilir. Bar getirisi backtest ile aynı tanımdır:
açılıştan bir sonraki açılışa (son barda kapanışa).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research import DEV_TRAIN_END, load, load_funding

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def train_frame(symbol: str, interval: str, market: str) -> pd.DataFrame:
    df = load(symbol, interval, market, scope="dev")
    df = df[df.index < DEV_TRAIN_END]
    return df


def train_funding(symbol: str) -> pd.DataFrame:
    f = load_funding(symbol, scope="dev")
    return f[f.index < DEV_TRAIN_END]


def bar_returns(df: pd.DataFrame) -> pd.Series:
    o = df["open"].to_numpy(float)
    c = df["close"].to_numpy(float)
    r = np.empty(len(o))
    r[:-1] = o[1:] / o[:-1] - 1.0
    r[-1] = c[-1] / o[-1] - 1.0
    return pd.Series(r, index=df.index)


def tstat(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x)))


# ---------------------------------------------------------------- tarama yardımcıları
import json
from pathlib import Path

from grafik_analiz.research import evaluate
from grafik_analiz.research.evaluate import backtest, compute_signals, load_data
from grafik_analiz.research.ledger import trials
from grafik_analiz.research.metrics import summarize

HERE = Path(__file__).resolve().parent
SONUC = HERE / "tarama_sonuclari.jsonl"
FAMILY = "mevsimsellik"


def _done() -> dict:
    out = {}
    if SONUC.exists():
        for line in SONUC.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["name"]] = row
    return out


def degerlendir(spec, asama: str, mults=(1.0, 2.0)) -> dict:
    """Yalnız dev_train penceresinde değerlendirir (deftere yazılır). Aynı ad iki kez değerlendirilmez."""
    done = _done()
    if spec.name in done:
        return done[spec.name]
    led = trials(FAMILY)
    if len(led) and (led["strateji"] == spec.name).any():
        raise RuntimeError(f"defterde var ama sonuç dosyasında yok: {spec.name}")
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=mults)
    row = {"name": spec.name, "asama": asama, "interval": spec.interval,
           "legs": [list(l) for l in spec.legs], "params": spec.params}
    for m in mults:
        r = res["dev_train"][m]
        k = "1x" if m == 1.0 else f"{m:g}x"
        for key in ("total_return", "sharpe", "max_drawdown", "trades", "cagr", "exposure", "total_costs", "total_funding", "skew", "kurtosis", "p_value", "win_rate", "avg_trade"):
            row[f"{key}_{k}"] = r.get(key)
    with SONUC.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=float) + "\n")
    return row


def train_backtest(spec, mult: float = 1.0):
    """dev_train'e kesilmiş veriyle backtest (tanı amaçlı; deftere yazılmaz).

    Yalnız deftere zaten yazılmış yapılandırmalar için kullanılır.
    """
    led = trials(FAMILY)
    if not (len(led) and (led["strateji"] == spec.name).any()):
        raise RuntimeError(f"önce evaluate() ile deftere yazılmalı: {spec.name}")
    data, funding = load_data(spec, "dev")
    data = {k: v[v.index < DEV_TRAIN_END] for k, v in data.items()}
    funding = {k: v[v.index < DEV_TRAIN_END] for k, v in funding.items()}
    sig = compute_signals(spec, data, funding)
    return backtest(spec, data, funding, sig, mult)


def yillik(spec, mult: float = 1.0) -> pd.Series:
    res = train_backtest(spec, mult)
    r = res.returns
    return (1 + r).groupby(r.index.year).prod() - 1
