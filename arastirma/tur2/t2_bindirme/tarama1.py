"""Tarama 1: taban çizgileri, (b) oynaklık yönetimi, (a) trend + carry. Yalnız dev_train."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ortak import KLASOR, degerlendir, log, yaz  # noqa: E402

from grafik_analiz.strategies.t2_bindirme import make_spec  # noqa: E402

FON = {
    "hep": dict(fon_n=0, fon_giris=0.0, fon_cikis=0.0),
    "f3": dict(fon_n=3, fon_giris=1e-4, fon_cikis=0.0),
    "f7": dict(fon_n=7, fon_giris=0.5e-4, fon_cikis=-0.5e-4),
}
LB = {"L10": (10, 20, 40), "L20": (20, 40, 80), "L40": (40, 80, 160)}


def konfigler():
    out = []
    # Taban çizgileri
    out.append(("t2_bindirme_altut_nakit_1d", "1d", dict(sinyal="sabit", sabit=1.0, bicim="nakit")))
    for fk, fv in FON.items():
        out.append((f"t2_bindirme_carry_saf_tam_4h_{fk}", "4h", dict(sinyal="sabit", sabit=0.0, bicim="tam", **fv)))
    # (b) oynaklık yönetimi, yalnız spot
    for hv in (0.4, 0.6, 0.8):
        for n in (10, 20, 40, 80):
            for bant in (0.0, 0.1):
                out.append((f"t2_bindirme_vol_nakit_1d_h{hv}_n{n}_b{bant}", "1d", dict(sinyal="vol", bicim="nakit", hedef_vol=hv, vol_gun=n, bant=bant)))
    # (b') oynaklık yönetimi + carry
    for hv in (0.4, 0.6):
        for n in (20, 40):
            for bicim in ("tam", "yarim"):
                out.append((f"t2_bindirme_vol_{bicim}_1d_h{hv}_n{n}_hep", "1d", dict(sinyal="vol", bicim=bicim, hedef_vol=hv, vol_gun=n, bant=0.1, **FON["hep"])))
    # (a) trend, nakit (tur 1 kıyası) ve carry'li
    for lk, lv in LB.items():
        for bant in (0.0, 0.15):
            out.append((f"t2_bindirme_trend_nakit_4h_{lk}_b{bant}", "4h", dict(sinyal="trend", bicim="nakit", lookbacks=lv, bant=bant)))
            for bicim in ("tam", "yarim"):
                for fk, fv in FON.items():
                    out.append((f"t2_bindirme_trend_{bicim}_4h_{lk}_b{bant}_{fk}", "4h", dict(sinyal="trend", bicim=bicim, lookbacks=lv, bant=bant, **fv)))
    # (a') trend × oynaklık
    for hv in (0.4, 0.6, 0.8):
        for bicim in ("nakit", "tam", "yarim"):
            extra = FON["hep"] if bicim != "nakit" else {}
            out.append((f"t2_bindirme_trendvol_{bicim}_4h_L20_h{hv}_n30_b0.1", "4h", dict(sinyal="trend_vol", bicim=bicim, lookbacks=LB["L20"], hedef_vol=hv, vol_gun=30, bant=0.1, **extra)))
    return out


def main():
    rows = []
    ks = konfigler()
    log(f"{len(ks)} yapılandırma")
    for i, (name, iv, kw) in enumerate(ks, 1):
        spec = make_spec(name, iv, **kw)
        row = degerlendir(spec)
        row.update({"interval": iv, **{k: str(v) for k, v in kw.items()}})
        rows.append(row)
        log(f"{i}/{len(ks)} {name} ret={row['ret']:.3f} sh={row['sharpe']:.2f} alfa={row['alfa']:.3f} t={row['alfa_t']:.2f} b={row['beta']:.2f} ret2={row['ret2']:.3f} islem={row['trades']} ({row['sure']}s)")
        yaz(rows, KLASOR / "tarama1.csv")
    log("BITTI")


if __name__ == "__main__":
    main()
