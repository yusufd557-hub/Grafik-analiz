"""Tarama 3: trend × oynaklık ve trend + carry çevresinde ince tarama. Yalnız dev_train."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ortak import KLASOR, degerlendir, log, yaz  # noqa: E402
from tarama1 import FON, LB  # noqa: E402

from grafik_analiz.strategies.t2_bindirme import make_spec  # noqa: E402

LB2 = {**LB, "L15": (15, 30, 60)}


def konfigler():
    out = []
    for lk in ("L10", "L20"):
        for hv in (0.3, 0.4, 0.5):
            out.append((f"t2_bindirme_trendvol_nakit_4h_{lk}_h{hv}_n30_b0.1", "4h", dict(sinyal="trend_vol", bicim="nakit", lookbacks=LB2[lk], hedef_vol=hv, vol_gun=30, bant=0.1)))
            for bicim in ("tam", "yarim"):
                out.append((f"t2_bindirme_trendvol_{bicim}_4h_{lk}_h{hv}_n30_b0.1_f7", "4h", dict(sinyal="trend_vol", bicim=bicim, lookbacks=LB2[lk], hedef_vol=hv, vol_gun=30, bant=0.1, **FON["f7"])))
    for bant in (0.0, 0.15):
        out.append((f"t2_bindirme_trend_yarim_4h_L15_b{bant}_f7", "4h", dict(sinyal="trend", bicim="yarim", lookbacks=LB2["L15"], bant=bant, **FON["f7"])))
    for bicim in ("tam", "yarim"):
        out.append((f"t2_bindirme_vol_{bicim}_1d_h0.4_n40_f7", "1d", dict(sinyal="vol", bicim=bicim, hedef_vol=0.4, vol_gun=40, bant=0.1, **FON["f7"])))
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
        log(f"{i}/{len(ks)} {name} ret={row['ret']:.3f} sh={row['sharpe']:.2f} alfa={row['alfa']:.3f} t={row['alfa_t']:.2f} b={row['beta']:.2f} ret2={row['ret2']:.3f} islem={row['trades']} a20_23={row['alfa_20_23']:.3f} a24={row['alfa_24']:.3f}")
        yaz(rows, KLASOR / "tarama3.csv")
    log("BITTI")


if __name__ == "__main__":
    main()
