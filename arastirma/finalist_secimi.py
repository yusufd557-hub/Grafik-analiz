"""FINALISTLER.md'deki seçim kuralını uygular (yalnız geliştirme dönemi verisi).

Çalıştırma:
    GRAFIK_ANALIZ_ARASTIRMA=<veri> python arastirma/finalist_secimi.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import backtest, compute_signals, load_data
from grafik_analiz.research.metrics import daily_returns, summarize
from grafik_analiz.research.protocol import PERIODS, STRESS_MULTIPLIER
from grafik_analiz.strategies import all_specs

ADAYLAR = [
    "trend_ens_spot_port3_1d",
    "trend_ens_spot_port3_4h",
    "trend_ens_spot_port3_4h_vt",
    "trend_ens_vadeli_port3_4h_alim",
    "od_dip_ret4h_fut_port3_1h",
    "od_dip_ens4_fut_port3_1h",
    "kirilim_kanal4h_spot",
    "kirilim_kanal4h_vadeli_uzun",
    "formasyon_ucgen_kama_4h_trend_uzun",
    "formasyon_ucgen_kama_4h_hacim_iki",
    "formasyon_hepsi_4h_trend_10bar_uzun",
    "ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot",
    "ml_1h_fu_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel_egspot",
    "ml_1h_sp_PORT3_hgb_reg_H6_k3.0_ortusen_uzun_temel",
    "ml_1h_sp_PORT3_hgb_reg_H4_k3.0_ortusen_uzun_temel-btc",
]
MIN_ISLEM = 30
KORELASYON_SINIRI = 0.70
EN_FAZLA = 3

OUT = Path(__file__).resolve().parent / "finalist_secimi.json"


def main() -> None:
    specs = {s.name: s for s in all_specs()}
    eksik = [n for n in ADAYLAR if n not in specs]
    if eksik:
        raise SystemExit(f"bulunamayan adaylar: {eksik}")

    start, end = PERIODS["dev_valid"]
    satirlar = []
    gunluk = {}
    for name in ADAYLAR:
        t0 = time.time()
        spec = specs[name]
        data, funding = load_data(spec, "dev")
        signals = compute_signals(spec, data, funding)
        olcu = {}
        for kat in (1.0, STRESS_MULTIPLIER):
            res = backtest(spec, data, funding, signals, kat)
            m = summarize(res.returns, res.trades, res.exposure, res.costs, res.funding, start, end)
            olcu[kat] = m
            if kat == 1.0:
                r = res.returns[(res.returns.index >= start) & (res.returns.index < end)]
                gunluk[name] = daily_returns(r)
        satir = {
            "ad": name,
            "aile": spec.family,
            "getiri_1x": olcu[1.0]["total_return"],
            "getiri_2x": olcu[STRESS_MULTIPLIER]["total_return"],
            "sharpe_1x": olcu[1.0]["sharpe"],
            "sharpe_2x": olcu[STRESS_MULTIPLIER]["sharpe"],
            "islem": olcu[1.0].get("trades", 0),
            "dusus": olcu[1.0]["max_drawdown"],
            "maruziyet": olcu[1.0].get("exposure"),
        }
        satirlar.append(satir)
        print(f"{name}: sharpe2x={satir['sharpe_2x']:.3f} islem={satir['islem']} ({time.time() - t0:.0f} sn)", flush=True)

    tablo = pd.DataFrame(satirlar).sort_values("sharpe_2x", ascending=False).reset_index(drop=True)
    korelasyon = pd.DataFrame(gunluk).fillna(0.0).corr()

    secilen: list[str] = []
    karar = []
    for row in tablo.itertuples():
        if row.islem < MIN_ISLEM:
            karar.append((row.ad, f"elendi: {row.islem} işlem < {MIN_ISLEM}"))
            continue
        if len(secilen) >= EN_FAZLA:
            karar.append((row.ad, "elendi: 3 finalist dolu"))
            continue
        yakin = [s for s in secilen if korelasyon.loc[row.ad, s] >= KORELASYON_SINIRI]
        if yakin:
            karar.append((row.ad, f"elendi: {yakin[0]} ile korelasyon {korelasyon.loc[row.ad, yakin[0]]:.2f}"))
            continue
        secilen.append(row.ad)
        karar.append((row.ad, "FİNALİST"))

    sonuc = {
        "kural": {"min_islem": MIN_ISLEM, "korelasyon_siniri": KORELASYON_SINIRI, "en_fazla": EN_FAZLA, "puan": "dev_valid 2x maliyet Sharpe"},
        "tablo": tablo.to_dict(orient="records"),
        "karar": [{"ad": a, "karar": k} for a, k in karar],
        "finalistler": secilen,
        "korelasyon": korelasyon.round(3).to_dict(),
    }
    OUT.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps({"finalistler": secilen, "karar": karar}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
