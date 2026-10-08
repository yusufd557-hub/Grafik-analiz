"""Trend ailesi arama betiği: yalnızca dev_train penceresi.

Kullanım:  python arastirma/trend/arama.py <aşama>

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`
ile değerlendirilir; deney defterine (arastirma/deneyler/trend.jsonl) otomatik yazılır.
Defterde aynı adla kaydı olan yapılandırma tekrar değerlendirilmez.
Özet satırları arastirma/trend/sonuclar_train.csv dosyasına eklenir.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

from grafik_analiz.research import evaluate
from grafik_analiz.research.ledger import trials
from grafik_analiz.strategies.trend import FAMILY, make_spec

HERE = Path(__file__).resolve().parent
CSV = HERE / "sonuclar_train.csv"

LOOKS = [(10,), (20,), (40,), (80,), (160,), (10, 20, 40, 80, 160)]
KINDS = ["tsmom", "sma", "emax", "donch"]


def config_name(market, universe, interval, kinds, lookbacks, mode, target_vol=None, vol_days=30, band=0.0, atr_mult=None):
    name = f"{'+'.join(kinds)}_L{'-'.join(str(x) for x in lookbacks)}_{market}_{universe}_{interval}_{mode}"
    if target_vol:
        name += f"_vt{target_vol}_vd{vol_days}"
    if band:
        name += f"_b{band}"
    if atr_mult:
        name += f"_atr{atr_mult}"
    return name


def cfg(market, universe, interval, kinds, lookbacks, mode, **kw):
    return dict(market=market, universe=universe, interval=interval, kinds=tuple(kinds), lookbacks=tuple(lookbacks), mode=mode, **kw)


def stage_configs(stage: str) -> list[dict]:
    out = []
    if stage in ("s1", "s2"):
        interval = "1d" if stage == "s1" else "4h"
        for k in KINDS:
            for lb in LOOKS:
                out.append(cfg("spot", "PORT3", interval, (k,), lb, "long"))
                out.append(cfg("futures", "PORT3", interval, (k,), lb, "longshort"))
    if stage == "s3":
        # Tek coinler (1d) ve fikirler arası topluluk; bakış süresi topluluğu (ENS).
        ens = LOOKS[-1]
        kind_sets = [(k,) for k in KINDS] + [tuple(KINDS)]
        for coin in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            for ks in kind_sets:
                out.append(cfg("spot", coin, "1d", ks, ens, "long"))
                out.append(cfg("futures", coin, "1d", ks, ens, "longshort"))
        for interval in ("1d", "4h"):
            out.append(cfg("spot", "PORT3", interval, tuple(KINDS), ens, "long"))
            out.append(cfg("futures", "PORT3", interval, tuple(KINDS), ens, "longshort"))
    if stage == "s4":
        ens = LOOKS[-1]
        mid = (20, 40, 80)
        allk = tuple(KINDS)
        for interval in ("1d", "4h"):
            # a) oynaklık hedefleme, spot portföy
            for ks in [("tsmom",), allk]:
                for tv in (0.4, 0.6, 0.8):
                    out.append(cfg("spot", "PORT3", interval, ks, ens, "long", target_vol=tv, vol_days=30, band=0.1))
            # b) vadeli yalnız alım
            for ks in [(k,) for k in KINDS] + [allk]:
                out.append(cfg("futures", "PORT3", interval, ks, ens, "long"))
            # c) dar topluluk (20, 40, 80)
            for ks in [(k,) for k in KINDS] + [allk]:
                out.append(cfg("spot", "PORT3", interval, ks, mid, "long"))
            # d) Donchian + ATR iz süren stop
            for lb in [(20,), ens]:
                for am in (2.5, 4.0):
                    out.append(cfg("spot", "PORT3", interval, ("donch",), lb, "long", atr_mult=am))
            # e) vadeli alım-satım + oynaklık hedefleme
            for tv in (0.4, 0.6):
                out.append(cfg("futures", "PORT3", interval, allk, ens, "longshort", target_vol=tv, vol_days=30, band=0.1))
    if stage == "s5":
        # Düzlüğün ortası olan (20, 40, 80) fikirler arası topluluk üzerinde son incelik.
        mid = (20, 40, 80)
        allk = tuple(KINDS)
        for interval in ("1d", "4h"):
            out.append(cfg("spot", "PORT3", interval, allk, mid, "long", target_vol=0.6, vol_days=30, band=0.1))
            out.append(cfg("futures", "PORT3", interval, allk, mid, "long"))
            out.append(cfg("futures", "PORT3", interval, allk, mid, "longshort"))
            out.append(cfg("futures", "PORT3", interval, allk, mid, "longshort", target_vol=0.6, vol_days=30, band=0.1))
        out.append(cfg("spot", "PORT3", "1h", allk, mid, "long"))
        out.append(cfg("futures", "PORT3", "1h", allk, mid, "long"))
        out.append(cfg("spot", "PORT3", "4h", allk, mid, "long", band=0.15))
    return out


def done_names() -> set:
    t = trials(FAMILY)
    if t.empty:
        return set()
    return set(t.loc[t["pencere"] == "dev_train", "strateji"])


def run_configs(configs: list[dict]) -> pd.DataFrame:
    done = done_names()
    rows = []
    for c in configs:
        name = config_name(**c)
        if name in done:
            continue
        spec = make_spec(name, **c)
        t0 = time.time()
        res = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))
        m1 = res["dev_train"][1.0]
        m2 = res["dev_train"][2.0]
        years = max(m1.get("days", 0), 1) / 365.25
        full = {"target_vol": None, "vol_days": 30, "band": 0.0, "atr_mult": None, **c}
        row = {
            "name": name,
            **{k: (str(v) if isinstance(v, tuple) else v) for k, v in full.items()},
            "ret1": m1.get("total_return"),
            "ret2": m2.get("total_return"),
            "cagr1": m1.get("cagr"),
            "sharpe1": m1.get("sharpe"),
            "sharpe2": m2.get("sharpe"),
            "maxdd1": m1.get("max_drawdown"),
            "vol1": m1.get("volatility"),
            "trades": m1.get("trades"),
            "trades_per_year": (m1.get("trades") or 0) / years,
            "exposure": m1.get("exposure"),
            "costs1": m1.get("total_costs"),
            "funding1": m1.get("total_funding"),
            "days": m1.get("days"),
            "start": m1.get("start"),
            "secs": round(time.time() - t0, 2),
        }
        rows.append(row)
        done.add(name)
        print(f"{name:70s} SR={row['sharpe1']:.2f} R1={row['ret1']:.2f} R2={row['ret2']:.2f} DD={row['maxdd1']:.2f} tr/y={row['trades_per_year']:.1f}", flush=True)
        pd.DataFrame([row]).to_csv(CSV, mode="a", header=not CSV.exists(), index=False)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    stage = sys.argv[1]
    configs = stage_configs(stage)
    print(f"aşama {stage}: {len(configs)} yapılandırma", flush=True)
    run_configs(configs)
