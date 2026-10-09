"""Arama yardımcıları: her yapılandırma evaluate() ile (dev_train, 1×) deftere yazılır,
ardından aynı sinyallerle dev_train penceresinde işlem düzeyi tanı ölçüleri hesaplanır
(işlem başına brüt kenar, maliyet, yıllık net). dev_valid'e bakılmaz.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import backtest, compute_signals, evaluate, load_data
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies import t2_emir_akisi as ea

assert PROTOCOL_VERSION == "2", "GRAFIK_ANALIZ_PROTOKOL=2 gerekli"

HERE = Path(__file__).resolve().parent
_MEMO: dict = {}


def memo_signal(data, funding, **params):
    key = (
        json.dumps(params, sort_keys=True, default=str),
        tuple((leg, len(df), int(df.index[-1].value)) for leg, df in sorted(data.items())),
    )
    if key not in _MEMO:
        _MEMO.clear()
        _MEMO[key] = ea.sinyal(data, funding, **params)
    return _MEMO[key]


FIELDS = [
    "name", "market", "interval", "params", "total_return", "sharpe", "max_drawdown", "trades",
    "alfa", "beta", "alfa_t", "exposure", "gross_pt_bps", "net_pt_bps", "cost_pt_bps", "win",
    "avg_bars", "gross_total", "cost_total", "y2020", "y2021", "y2022", "y2023", "y2024", "sec",
    "leg_BTC", "leg_ETH", "leg_SOL",
]


def degerlendir(name: str, market: str, interval: str, csv_name: str, cost2: bool = False, **params) -> dict:
    spec = ea.make_spec(name, market, interval, **params)
    spec.signal_fn = memo_signal
    t0 = time.time()
    mults = (1.0, 2.0) if cost2 else (1.0,)
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=mults)
    m = res["dev_train"][1.0]
    data, funding = load_data(spec, "dev")
    sig = compute_signals(spec, data, funding)
    rr = backtest(spec, data, funding, sig, 1.0)
    w = spec.leg_weights()
    g_list, n_list = [], []
    gross_total = 0.0
    cost_total = 0.0
    leg_ret = {}
    for leg, lr in rr.legs.items():
        ln = lr.net[lr.net.index < DEV_TRAIN_END]
        leg_ret["leg_" + leg[1][:3]] = float((1.0 + ln).prod() - 1.0)
        t = lr.trades
        t = t[t["entry_time"] < DEV_TRAIN_END]
        g_list.append(t["gross_return"].to_numpy())
        n_list.append(t["net_return"].to_numpy())
        gross_total += w[leg] * float(lr.gross[lr.gross.index < DEV_TRAIN_END].sum())
        cost_total += w[leg] * float(lr.cost[lr.cost.index < DEV_TRAIN_END].sum())
    g = np.concatenate(g_list) if g_list else np.array([])
    nn = np.concatenate(n_list) if n_list else np.array([])
    r = rr.returns[rr.returns.index < DEV_TRAIN_END]
    yearly = (1.0 + r).groupby(r.index.year).prod() - 1.0
    row = {
        "name": spec.name,
        "market": market,
        "interval": interval,
        "params": json.dumps(params, sort_keys=True),
        "total_return": m.get("total_return"),
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "trades": m.get("trades"),
        "alfa": m.get("alfa"),
        "beta": m.get("beta"),
        "alfa_t": m.get("alfa_t"),
        "exposure": m.get("exposure"),
        "gross_pt_bps": float(np.mean(g) * 1e4) if len(g) else float("nan"),
        "net_pt_bps": float(np.mean(nn) * 1e4) if len(nn) else float("nan"),
        "cost_pt_bps": float((np.mean(g) - np.mean(nn)) * 1e4) if len(g) else float("nan"),
        "win": float(np.mean(nn > 0)) if len(nn) else float("nan"),
        "avg_bars": m.get("avg_bars"),
        "gross_total": gross_total,
        "cost_total": cost_total,
        "sec": round(time.time() - t0, 1),
        "wo_best": m.get("total_without_best"),
        "p_value": m.get("p_value"),
        "win_rate": m.get("win_rate"),
    }
    for y in range(2020, 2025):
        row[f"y{y}"] = float(yearly.get(y, float("nan")))
    row.update(leg_ret)
    if cost2:
        row["ret_2x"] = res["dev_train"][2.0].get("total_return")
        row["sharpe_2x"] = res["dev_train"][2.0].get("sharpe")
    path = HERE / csv_name
    new = not path.exists()
    # tarama1/tarama2 dosyaları eski başlıkla yazıldı; sonrakiler ek sütunlarla.
    fields = FIELDS + (["ret_2x"] if cost2 else [])
    if csv_name not in ("tarama1.csv", "tarama2.csv"):
        fields = FIELDS + ["wo_best", "p_value", "win_rate", "ret_2x", "sharpe_2x"]
    with path.open("a", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if new:
            wr.writeheader()
        wr.writerow(row)
    _print(row)
    return row


def _f(x, pct=False, d=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "nan"
    return f"{x * 100:+.{d}f}%" if pct else f"{x:+.{d}f}"


def _print(row: dict) -> None:
    print(
        f"{row['name'][:70]:70s} ret {_f(row['total_return'], True, 1):>9s} sh {_f(row['sharpe']):>6s} "
        f"dd {_f(row['max_drawdown'], True, 1):>7s} n {row['trades']:>6} a {_f(row['alfa'], True, 1):>8s} "
        f"b {_f(row['beta']):>6s} g/t {row['gross_pt_bps']:+7.1f} n/t {row['net_pt_bps']:+7.1f} "
        f"exp {row['exposure'] or 0:.2f} yrs " + " ".join(_f(row[f'y{y}'], True, 0) for y in range(2020, 2025))
        + (f" 2x {_f(row.get('ret_2x'), True, 1)}" if "ret_2x" in row else "")
        + (f" wob {_f(row.get('wo_best'), True, 0)}" if row.get("wo_best") is not None else "")
        + " | " + " ".join(f"{k[4:]} {_f(v, True, 0)}" for k, v in row.items() if k.startswith("leg_"))
        + f" [{row['sec']}s]",
        flush=True,
    )
