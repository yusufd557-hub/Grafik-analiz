"""Tur 2: ileriye dönük takibe seçim (docs/PROTOKOL_2.md, "İleriye dönük takibe seçim").

Kural sonuçlardan önce yazıldı (arastirma/tur2/FINALISTLER.md) ve mekaniktir:

1. Adaylar: `grafik_analiz/strategies/t2_*.py` dosyalarındaki bütün dondurulmuş
   yapılandırmalardan candidate_check'i (protokol 2, yedi şart) geçenler.
2. İç doğrulamada en az 30 işlem yapmamış adaylar elenir.
3. Kalanlar iç doğrulamada iki kat maliyetle Sharpe'a göre sıralanır.
4. Sırayla, daha önce seçilenlerin hepsiyle iç doğrulama günlük getiri
   korelasyonu 0,70'ten küçük olan seçilir; en fazla 5.

Denetimde (arastirma/tur2/DENETIM_2.md) kritik ihlal ya da ileri bakış hatası
bulunan yapılandırmalar `--haric` ile, gerekçesi FINALISTLER.md'ye yazılarak
sıralamadan önce çıkarılır.

Çalıştırma:
    GRAFIK_ANALIZ_PROTOKOL=2 GRAFIK_ANALIZ_ARASTIRMA=<veri> \\
        python arastirma/tur2/finalist_secimi.py [--haric ad1,ad2]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import backtest, benchmark_daily, candidate_check, compute_signals, load_data
from grafik_analiz.research.metrics import alpha_beta, daily_returns, summarize, window
from grafik_analiz.research.protocol import MAX_FORWARD_FINALISTS, PERIODS, PROTOCOL_VERSION, STRESS_MULTIPLIER
from grafik_analiz.strategies import all_specs

AILE_ONEKI = "t2_"
MIN_ISLEM = 30
KORELASYON_SINIRI = 0.70
EN_FAZLA = MAX_FORWARD_FINALISTS

OUT = Path(__file__).resolve().parent / "finalist_secimi.json"


def olc(spec) -> tuple[dict, pd.Series]:
    """evaluate() ile aynı ölçüler (deftere yazmadan) ve iç doğrulama günlük getirisi."""
    data, funding = load_data(spec, "dev")
    signals = compute_signals(spec, data, funding)
    bench = benchmark_daily(spec, "dev")
    sonuc: dict = {}
    gunluk = None
    for kat in (1.0, STRESS_MULTIPLIER):
        res = backtest(spec, data, funding, signals, kat)
        for w in ("dev_train", "dev_valid"):
            start, end = PERIODS[w]
            m = summarize(res.returns, res.trades, res.exposure, res.costs, res.funding, start, end)
            if not bench.empty:
                m.update(alpha_beta(daily_returns(window(res.returns, start, end)), bench))
            sonuc.setdefault(w, {})[kat] = m
            if w == "dev_valid" and kat == 1.0:
                gunluk = daily_returns(window(res.returns, start, end))
    return sonuc, gunluk


def main() -> None:
    if PROTOCOL_VERSION != "2":
        raise SystemExit("GRAFIK_ANALIZ_PROTOKOL=2 ile çalıştırın")
    parser = argparse.ArgumentParser()
    parser.add_argument("--haric", default="", help="denetimde elenen yapılandırmalar, virgülle")
    args = parser.parse_args()
    haric = {a for a in args.haric.split(",") if a}

    specs = [s for s in all_specs() if s.family.startswith(AILE_ONEKI)]
    bilinmeyen = haric - {s.name for s in specs}
    if bilinmeyen:
        raise SystemExit(f"bulunamayan --haric adları: {sorted(bilinmeyen)}")

    satirlar = []
    gunluk = {}
    for spec in specs:
        t0 = time.time()
        sonuc, g = olc(spec)
        kontrol = candidate_check(sonuc)
        v1, v2 = sonuc["dev_valid"][1.0], sonuc["dev_valid"][STRESS_MULTIPLIER]
        satirlar.append(
            {
                "ad": spec.name,
                "aile": spec.family,
                "aday": bool(kontrol["aday"]),
                "gecemedigi": [k for k, ok in kontrol.items() if k != "aday" and not ok],
                "getiri_1x": v1["total_return"],
                "getiri_2x": v2["total_return"],
                "sharpe_1x": v1["sharpe"],
                "sharpe_2x": v2["sharpe"],
                "islem": v1.get("trades", 0),
                "dusus": v1["max_drawdown"],
                "alfa": v1.get("alfa"),
                "alfa_t": v1.get("alfa_t"),
                "beta": v1.get("beta"),
                "egitim_alfa": sonuc["dev_train"][1.0].get("alfa"),
            }
        )
        gunluk[spec.name] = g
        print(f"{spec.name}: aday={kontrol['aday']} sharpe2x={v2['sharpe']:.3f} islem={v1.get('trades', 0)} ({time.time() - t0:.0f} sn)", flush=True)

    tablo = pd.DataFrame(satirlar)
    korelasyon = pd.DataFrame(gunluk).fillna(0.0).corr()
    sirali = tablo[tablo["aday"]].sort_values("sharpe_2x", ascending=False)

    secilen: list[str] = []
    karar = []
    for row in sirali.itertuples():
        if row.ad in haric:
            karar.append((row.ad, "elendi: denetim (FINALISTLER.md)"))
            continue
        if row.islem < MIN_ISLEM:
            karar.append((row.ad, f"elendi: {row.islem} işlem < {MIN_ISLEM}"))
            continue
        if len(secilen) >= EN_FAZLA:
            karar.append((row.ad, f"elendi: {EN_FAZLA} yer dolu"))
            continue
        yakin = [s for s in secilen if korelasyon.loc[row.ad, s] >= KORELASYON_SINIRI]
        if yakin:
            karar.append((row.ad, f"elendi: {yakin[0]} ile korelasyon {korelasyon.loc[row.ad, yakin[0]]:.2f}"))
            continue
        secilen.append(row.ad)
        karar.append((row.ad, "TAKİBE ALINIR"))

    sonuc = {
        "protokol": PROTOCOL_VERSION,
        "kural": {
            "aday": "candidate_check (protokol 2)",
            "min_islem": MIN_ISLEM,
            "korelasyon_siniri": KORELASYON_SINIRI,
            "en_fazla": EN_FAZLA,
            "puan": "dev_valid 2x maliyet Sharpe",
        },
        "haric": sorted(haric),
        "tablo": tablo.to_dict(orient="records"),
        "karar": [{"ad": a, "karar": k} for a, k in karar],
        "secilenler": secilen,
        "korelasyon": korelasyon.round(3).to_dict(),
    }
    OUT.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"secilenler": secilen, "karar": karar}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
