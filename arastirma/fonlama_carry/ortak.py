"""Tarama betikleri için ortak yardımcılar. Tarama sırasında yalnız dev_train penceresi değerlendirilir."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import COSTS, DEV_TRAIN_END, evaluate, run
from grafik_analiz.strategies.fonlama_carry import make_spec

KLASOR = Path(__file__).resolve().parent


def ad(kind: str, universe: str, interval: str, p: dict) -> str:
    parca = [kind, universe, interval] + [f"{k}{v}" for k, v in p.items()]
    return "_".join(str(x) for x in parca)


def _yillik_ciro(spec, r1: dict) -> float:
    # Ağırlıklı ciro ≈ toplam maliyet / taraf başına ortalama maliyet (bacak piyasalarına göre)
    ps = np.mean([COSTS[leg[0]].per_side for leg in spec.legs])
    yil = r1["days"] / 365.25
    return r1.get("total_costs", 0) / ps / yil if yil else float("nan")


def tara(satirlar: list[tuple[str, str, str, dict]], cikti: str, maliyetler=(1.0, 2.0)) -> pd.DataFrame:
    """satirlar: (kind, universe, interval, params). dev_train sonuçlarını CSV'ye yazar (ekleyerek)."""
    kayit = []
    t0 = time.time()
    for kind, universe, interval, p in satirlar:
        spec = make_spec(ad(kind, universe, interval, p), kind, universe, interval, p)
        res = evaluate(spec, windows=("dev_train",), cost_multipliers=maliyetler)
        r1 = res["dev_train"][1.0]
        r2 = res["dev_train"].get(2.0, {})
        kayit.append(
            {
                "ad": spec.name,
                "kind": kind,
                "universe": universe,
                "interval": interval,
                "params": json.dumps(p, ensure_ascii=False),
                "getiri": r1.get("total_return"),
                "cagr": r1.get("cagr"),
                "sharpe": r1.get("sharpe"),
                "maxdd": r1.get("max_drawdown"),
                "islem": r1.get("trades"),
                "maruz": r1.get("exposure"),
                "yillik_ciro": _yillik_ciro(spec, r1),
                "fonlama": r1.get("total_funding"),
                "maliyet": r1.get("total_costs"),
                "getiri_2x": r2.get("total_return"),
                "sharpe_2x": r2.get("sharpe"),
                "gun": r1.get("days"),
                "baslangic": r1.get("start"),
            }
        )
        print(f"{spec.name:70s} {r1.get('total_return', float('nan')):8.3f} S={r1.get('sharpe') or float('nan'):6.2f} "
              f"DD={r1.get('max_drawdown', float('nan')):7.3f} n={r1.get('trades')} 2x={r2.get('total_return', float('nan')):8.3f}",
              flush=True)
    df = pd.DataFrame(kayit)
    path = KLASOR / cikti
    df.to_csv(path, mode="a", header=not path.exists(), index=False)
    print(f"{len(satirlar)} yapılandırma, {time.time() - t0:.0f} sn")
    return df


def ayristir(kind: str, universe: str, interval: str, p: dict, cost_multiplier: float = 1.0) -> dict:
    """dev_train içinde getiri ayrıştırması (aritmetik toplamlar): fiyat, maliyet, fonlama + yıllık net.

    run() bütün geliştirme verisiyle sinyal üretir; seriler hemen DEV_TRAIN_END'de kesilir,
    iç doğrulama dönemine bakılmaz. Yapılandırma önceden evaluate() ile deftere yazılmış olmalıdır.
    """
    spec = make_spec("ayristir", kind, universe, interval, p)
    res = run(spec, "dev", cost_multiplier)
    w = spec.leg_weights()
    cut = lambda s: s[s.index < DEV_TRAIN_END]
    fiyat = sum(w[leg] * cut(lr.gross).sum() for leg, lr in res.legs.items())
    maliyet = float(cut(res.costs).sum())
    fon = float(cut(res.funding).sum())
    r = cut(res.returns)
    yillik = ((1 + r).groupby(r.index.year).prod() - 1).round(4).to_dict()
    t = res.trades[res.trades["entry_time"] < DEV_TRAIN_END]
    islem = t.groupby(pd.DatetimeIndex(t["entry_time"]).year).size().to_dict()
    return {"fiyat_toplam": float(fiyat), "maliyet_toplam": maliyet, "fonlama_alinan": -fon, "net_toplam": float(r.sum()),
            "yillik": yillik, "yillik_islem": islem}
