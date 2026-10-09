"""Ortak tarama yardımcısı: yalnız dev_train, harness `evaluate` ile (deftere yazılır)."""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import evaluate
from grafik_analiz.strategies.t2_genis_evren import DEFAULTS, make_spec

assert protocol.PROTOCOL_VERSION == "2"

KISA = {"skor": "", "reb": "r", "k_oran": "k", "tampon": "t", "yan": "", "boyut": "", "notr": "",
        "top_n": "n", "beta_gun": "bg", "oyn_gun": "og", "min_uye": "mu", "k_min": "km", "delist_cik": "dl"}
COLS = ["ad", "aralik", "parametreler", "kat", "total_return", "sharpe", "max_drawdown", "trades", "alfa", "beta",
        "alfa_t", "exposure", "total_costs", "total_funding", "volatility", "p_value"]


def name_for(interval: str, params: dict) -> str:
    full = {**DEFAULTS, **params}
    parts = [interval]
    for k, short in KISA.items():
        if k in params and params[k] != DEFAULTS.get(k) or k in ("skor", "reb", "k_oran"):
            v = full[k]
            v = str(v).replace(".", "").replace("+", "P")
            parts.append(f"{short}{v}")
    return "t2_genis_evren_" + "_".join(parts)


def run_grid(configs: list[tuple[str, dict]], out_csv: Path, mults=(1.0,)) -> None:
    done = set()
    if out_csv.exists():
        with out_csv.open() as fh:
            for row in csv.DictReader(fh):
                done.add((row["aralik"], row["parametreler"]))
    new = not out_csv.exists()
    with out_csv.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if new:
            w.writeheader()
        for interval, params in configs:
            key = json.dumps({**DEFAULTS, **params}, sort_keys=True)
            if (interval, key) in done:
                continue
            name = name_for(interval, params)
            spec = make_spec(name, interval, params)
            t0 = time.time()
            res = evaluate(spec, windows=("dev_train",), cost_multipliers=tuple(mults))
            for mult in mults:
                m = res["dev_train"][mult]
                w.writerow({"ad": name, "aralik": interval, "parametreler": key, "kat": mult,
                            **{c: m.get(c) for c in COLS[4:]}})
            fh.flush()
            m = res["dev_train"][1.0]
            print(f"{name:70s} getiri {m['total_return']:+.4f} sharpe {m['sharpe']:+.2f} alfa {m['alfa']:+.4f} "
                  f"beta {m['beta']:+.3f} t {m['alfa_t']:+.2f} işlem {m['trades']} ({time.time()-t0:.0f}s)", flush=True)
