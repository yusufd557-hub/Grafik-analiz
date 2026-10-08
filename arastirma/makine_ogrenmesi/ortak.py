"""Arama yardımcıları. Arama sırasında YALNIZ dev_train penceresi kullanılır."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import evaluate, run
from grafik_analiz.research.ledger import trials
from grafik_analiz.research.metrics import daily_returns, sharpe
from grafik_analiz.strategies import makine_ogrenmesi as mo

KLASOR = Path(__file__).resolve().parent
SONUC = KLASOR / "tarama_sonuclari.jsonl"
TRAIN_END = pd.Timestamp("2024-01-01", tz="UTC")

KISA = {"model": "", "H": "H", "k": "k", "esleme": "", "yon": "", "pencere_gun": "w", "min_gun": "mg",
        "min_satir": "ms", "yeniden": "re", "ozellik": "", "adim": "ad", "C": "C", "hgb_iter": "it",
        "hgb_lr": "lr", "hgb_yaprak": "yp", "hgb_min_yaprak": "my", "hgb_l2": "l2", "egitim": "eg"}


def ad_uret(interval: str, market: str, universe: str, params: dict) -> str:
    p = {**mo.DEFAULTS, **params}
    if market == "spot":
        p["yon"] = "uzun"
    parca = [f"ml_{interval}_{'sp' if market == 'spot' else 'fu'}_{universe}", p["model"], f"H{p['H']}", f"k{p['k']}",
             p["esleme"], p["yon"], p["ozellik"].replace("+", "-")]
    for key in ("pencere_gun", "min_gun", "min_satir", "yeniden", "adim", "C", "hgb_iter", "hgb_lr", "hgb_yaprak", "hgb_min_yaprak", "hgb_l2", "egitim"):
        if p[key] != mo.DEFAULTS[key]:
            parca.append(f"{KISA[key]}{p[key]}")
    return "_".join(str(x) for x in parca)


def onceki_adlar() -> set:
    t = trials(mo.FAMILY)
    if t.empty:
        return set()
    return set(t.loc[t["pencere"] == "dev_train", "strateji"])


def degerlendir(interval: str, market: str, universe: str = "PORT3", asama: str = "", **params) -> dict | None:
    ad = ad_uret(interval, market, universe, params)
    if ad in onceki_adlar():
        print(f"  (zaten var) {ad}", flush=True)
        return None
    spec = mo.make_spec(ad, interval, market, universe, **params)
    t0 = time.time()
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))
    m1, m2 = res["dev_train"][1.0], res["dev_train"][2.0]
    row = {
        "asama": asama, "ad": ad, "interval": interval, "market": market, "universe": universe,
        **{k: v for k, v in spec.params.items()},
        "ret1": m1.get("total_return"), "sh1": m1.get("sharpe"), "mdd1": m1.get("max_drawdown"),
        "tr1": m1.get("trades"), "exp1": m1.get("exposure"), "cost1": m1.get("total_costs"),
        "ret2": m2.get("total_return"), "sh2": m2.get("sharpe"), "start": m1.get("start"),
        "sure": round(time.time() - t0, 1),
    }
    with SONUC.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=float) + "\n")
    print(f"  {ad}: ret1={row['ret1']:.3f} sh1={row['sh1']:.2f} ret2={row['ret2']:.3f} sh2={row['sh2']:.2f} "
          f"mdd={row['mdd1']:.2f} tr={row['tr1']} exp={row['exp1']:.2f} cost={row['cost1']:.2f} ({row['sure']}s)", flush=True)
    return row


def sonuclar() -> pd.DataFrame:
    if not SONUC.exists():
        return pd.DataFrame()
    return pd.read_json(SONUC, lines=True)


def yillik(interval: str, market: str, universe: str = "PORT3", cost: float = 1.0, **params) -> pd.DataFrame:
    """Defterde zaten bulunan bir yapılandırmanın dev_train içi yıllık dökümü.

    Getiri serisi metrik hesaplanmadan ÖNCE 2024-01-01'de kesilir.
    """
    ad = ad_uret(interval, market, universe, params)
    assert ad in onceki_adlar(), f"önce degerlendir(): {ad}"
    spec = mo.make_spec(ad, interval, market, universe, **params)
    res = run(spec, "dev", cost)
    r = res.returns[res.returns.index < TRAIN_END]
    rows = []
    for y, g in r.groupby(r.index.year):
        d = daily_returns(g)
        rows.append({"yil": y, "getiri": float((1 + g).prod() - 1), "sharpe": sharpe(d)})
    bacak = {}
    for leg, lr in res.legs.items():
        n = lr.net[lr.net.index < TRAIN_END]
        bacak[f"{leg[0][:2]}:{leg[1][:3]}"] = float((1 + n).prod() - 1)
    out = pd.DataFrame(rows)
    out.attrs["bacak"] = bacak
    return out
