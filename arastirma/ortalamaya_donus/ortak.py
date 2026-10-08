"""Arama betikleri için ortak yardımcılar (yalnız dev_train penceresi).

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,))`
ile değerlendirilir; sonuç deney defterine otomatik yazılır. Buradaki satır
yalnızca ek tanılama içindir (işlem başına brüt kenar).
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

from grafik_analiz.research import evaluate
from grafik_analiz.strategies.ortalamaya_donus import make_spec

KLASOR = Path(__file__).resolve().parent

RT_COST = {"futures": 0.0014, "spot": 0.0024}


def spec_name(market: str, universe: str, interval: str, params: dict) -> str:
    parts = [market[:3], universe, interval]
    for k in sorted(params):
        v = params[k]
        if k == "components":
            v = "ens" + str(len(v)) + "-" + hashlib.sha1(json.dumps(v, sort_keys=True).encode()).hexdigest()[:8]
        parts.append(f"{k}={v}")
    return "od_" + "_".join(str(p) for p in parts)


def degerlendir(market: str, universe: str, interval: str, params: dict, mults=(1.0,)) -> dict:
    name = spec_name(market, universe, interval, params)
    spec = make_spec(name, market, universe, interval, **params)
    t0 = time.time()
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=tuple(mults))
    m = res["dev_train"][1.0]
    n_legs = len(spec.legs)
    trades = m.get("trades", 0) or 0
    row = {
        "name": name,
        "market": market,
        "universe": universe,
        "interval": interval,
        "params": json.dumps(params, sort_keys=True),
        "total_return": m.get("total_return"),
        "sharpe": m.get("sharpe"),
        "max_dd": m.get("max_drawdown"),
        "trades": trades,
        "exposure": m.get("exposure"),
        "win_rate": m.get("win_rate"),
        "avg_bars": m.get("avg_bars"),
        "costs": m.get("total_costs"),
        "funding": m.get("total_funding"),
        "secs": round(time.time() - t0, 1),
    }
    if trades:
        # Bacak birimi (pozisyon 1) başına: net ve brüt işlem kenarı.
        net_pt = m["avg_trade"] * n_legs
        gross_pt = (m["avg_trade"] * trades + m["total_costs"] + m["total_funding"]) / trades * n_legs
        row["net_per_trade"] = net_pt
        row["gross_per_trade"] = gross_pt
        row["edge_over_cost"] = gross_pt / RT_COST[market]
    for mult in mults:
        if mult != 1.0:
            row[f"total_return_{mult}x"] = res["dev_train"][mult].get("total_return")
    return row


def calistir(configs: list[tuple], out_csv: str, mults=(1.0,)) -> pd.DataFrame:
    """configs: (market, universe, interval, params) listesi."""
    rows = []
    path = KLASOR / out_csv
    for i, (market, universe, interval, params) in enumerate(configs):
        row = degerlendir(market, universe, interval, params, mults)
        rows.append(row)
        pd.DataFrame(rows).to_csv(path, index=False)
        print(
            f"[{i + 1}/{len(configs)}] {row['name']} ret={row['total_return']:.3f} sh={row['sharpe']:.2f} "
            f"n={row['trades']} gross/tr={row.get('gross_per_trade', float('nan')):.4%} "
            f"net/tr={row.get('net_per_trade', float('nan')):.4%} ({row['secs']}s)",
            flush=True,
        )
        sys.stdout.flush()
    return pd.DataFrame(rows)
