"""Tarama betikleri için ortak yardımcılar. Yalnız dev_train penceresi değerlendirilir."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from grafik_analiz.research import evaluate, COSTS
from grafik_analiz.strategies.rotasyon import make_spec

KLASOR = Path(__file__).resolve().parent


def ad(kind: str, evren: str, p: dict) -> str:
    parca = [kind, evren] + [f"{k}{v}" for k, v in p.items() if k not in ("alt", "baz")]
    if kind == "oran":
        parca.insert(2, f"{p['alt'][:3]}{p['baz'][:3]}")
    return "_".join(str(x) for x in parca)


def tara(satirlar: list[tuple[str, str, tuple, dict]], cikti: str, maliyetler=(1.0, 2.0)) -> pd.DataFrame:
    """satirlar: (kind, evren_adi, legs, params). dev_train sonuçlarını CSV'ye yazar."""
    kayit = []
    for kind, evren, legs, p in satirlar:
        spec = make_spec(ad(kind, evren, p), kind, legs, p)
        res = evaluate(spec, windows=("dev_train",), cost_multipliers=maliyetler)
        r1 = res["dev_train"][1.0]
        r2 = res["dev_train"].get(2.0, {})
        per_side = COSTS[legs[0][0]].per_side
        yil = r1["days"] / 365.25
        kayit.append(
            {
                "ad": spec.name,
                "kind": kind,
                "evren": evren,
                "params": json.dumps(p, ensure_ascii=False),
                "getiri": r1.get("total_return"),
                "cagr": r1.get("cagr"),
                "sharpe": r1.get("sharpe"),
                "maxdd": r1.get("max_drawdown"),
                "islem": r1.get("trades"),
                "maruz": r1.get("exposure"),
                "yillik_ciro": r1.get("total_costs", 0) / per_side / yil if yil else None,
                "fonlama": r1.get("total_funding"),
                "getiri_2x": r2.get("total_return"),
                "sharpe_2x": r2.get("sharpe"),
                "gun": r1.get("days"),
            }
        )
        print(spec.name, round(r1.get("total_return", float("nan")), 3), round(r1.get("sharpe") or float("nan"), 2), flush=True)
    df = pd.DataFrame(kayit)
    df.to_csv(KLASOR / cikti, index=False)
    return df


def yillik(kind: str, legs, p: dict) -> pd.Series:
    """dev_train içinde takvim yılı net getirileri (1× maliyet).

    run() bütün geliştirme verisiyle sinyal üretir; getiri serisi hemen
    DEV_TRAIN_END'de kesilir, iç doğrulama dönemine bakılmaz. Yapılandırma
    ayrıca evaluate() ile deftere yazılmış olmalıdır.
    """
    from grafik_analiz.research import run, DEV_TRAIN_END

    spec = make_spec("yillik", kind, legs, p)
    r = run(spec, "dev").returns
    r = r[r.index < DEV_TRAIN_END]
    return (1 + r).groupby(r.index.year).prod() - 1


def yillik_islem(kind: str, legs, p: dict) -> tuple[pd.Series, pd.Series]:
    """dev_train içinde yıllık net getiri ve yıllık işlem sayısı (giriş zamanına göre)."""
    from grafik_analiz.research import run, DEV_TRAIN_END

    spec = make_spec("yillik", kind, legs, p)
    res = run(spec, "dev")
    r = res.returns[res.returns.index < DEV_TRAIN_END]
    t = res.trades[res.trades["entry_time"] < DEV_TRAIN_END]
    return (1 + r).groupby(r.index.year).prod() - 1, t.groupby(pd.DatetimeIndex(t["entry_time"]).year).size()
