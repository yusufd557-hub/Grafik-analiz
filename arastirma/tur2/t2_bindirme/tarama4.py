"""Tarama 4: önceden yazılmış kuralla (NOTLAR.md bölüm 2) portföy bileşen seçimi ve portföy çeşitleri.

Girdi: tarama2.csv (harness eğitim ölçüleri + alt dönem alfaları) ve bilesen_gunluk.csv
(eğitim günlük getirileri, veri 31.12.2024'te kesik). Yalnız dev_train.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from ortak import KLASOR, T2020, TRAIN_END, degerlendir, log, yaz  # noqa: E402

from grafik_analiz.strategies.t2_bindirme import make_portfolio_spec  # noqa: E402

MAX_K = 4
KORELASYON = 0.50


def sec(t2: pd.DataFrame, gun: pd.DataFrame, alt_sart: bool = True) -> list[str]:
    ok = (t2.ret > 0) & (t2.ret2 > 0) & (t2.alfa > 0) & (t2.alfa_t >= 1.0)
    if alt_sart:
        ok &= (t2.alfa_20_23 > 0) & (t2.alfa_24 > 0)
    aday = t2[ok].sort_values("alfa_t", ascending=False)
    g = gun[(gun.index >= T2020) & (gun.index < TRAIN_END)]
    secilen: list[str] = []
    for name in aday.bilesen:
        if all(abs(g[name].corr(g[s])) < KORELASYON for s in secilen):
            secilen.append(name)
        if len(secilen) >= MAX_K:
            break
    return secilen


def main():
    t2 = pd.read_csv(KLASOR / "tarama2.csv")
    gun = pd.read_csv(KLASOR / "bilesen_gunluk.csv", index_col=0, parse_dates=True)
    gun.index = pd.to_datetime(gun.index, utc=True)
    secilen = sec(t2, gun, True)
    kural = "alt dönem şartıyla"
    if len(secilen) < 2:
        secilen = sec(t2, gun, False)
        kural = "alt dönem şartı kaldırılarak (madde 6)"
    g = gun[(gun.index >= T2020) & (gun.index < TRAIN_END)]
    vol = {s: float(g[s].std() * np.sqrt(365)) for s in secilen}
    kor = g[secilen].corr().round(3)
    log(f"seçilen ({kural}): {secilen}")
    log(f"oynaklık 2020–2024: {vol}")
    log(f"korelasyon:\n{kor.to_string()}")
    if len(secilen) < 2:
        log("portföy yapılmaz")
        return
    ters = {s: 1.0 / vol[s] for s in secilen}
    toplam = sum(ters.values())
    cesit = {
        "esit_sermaye": {s: 1.0 / len(secilen) for s in secilen},
        "esit_risk_sermaye": {s: ters[s] / toplam for s in secilen},
        "esit_risk_h0.10": {s: min(3.0, 0.10 / vol[s]) for s in secilen},
        "esit_risk_h0.20": {s: min(3.0, 0.20 / vol[s]) for s in secilen},
    }
    (KLASOR / "portfoy_secimi.json").write_text(
        json.dumps({"kural": kural, "secilen": secilen, "oynaklik_2020_2024": vol, "korelasyon": kor.to_dict(), "cesitler": cesit}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rows = []
    for ad, b in cesit.items():
        spec = make_portfolio_spec(f"t2_bindirme_portfoy_{ad}", list(b), list(b.values()))
        row = degerlendir(spec)
        row.update({"bilesenler": json.dumps(list(b)), "carpanlar": json.dumps([round(v, 6) for v in b.values()])})
        rows.append(row)
        log(f"{ad} ret={row['ret']:.3f} ret2={row['ret2']:.3f} sh={row['sharpe']:.2f} alfa={row['alfa']:.3f} t={row['alfa_t']:.2f} b={row['beta']:.2f} "
            f"islem={row['trades']} a20_23={row['alfa_20_23']:.3f} a24={row['alfa_24']:.3f} ({row['sure']}s)")
        yaz(rows, KLASOR / "tarama4.csv")
    log("BITTI")


if __name__ == "__main__":
    main()
