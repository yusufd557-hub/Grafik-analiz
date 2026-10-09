"""Ters seçilim tanısı (yalnız dev_train; veri DEV_TRAIN_END'de kesilir, deftere yazılmaz).

Defterde zaten değerlendirilmiş yapılandırmalar için giriş bölümleri (sinyal + m bar
yeniden deneme) incelenir:

- dolum oranı (bölüm başına),
- "piyasa emriyle girilseydi" getirisi: sinyalden sonraki açılışta giriş, H bar tutma
  (dolan ve dolmayan bölümler ayrı ayrı),
- dolan bölümlerin limit fiyattan H bar getirisi,
- toplam brüt katkı: bütün bölümler piyasa emriyle vs yalnız dolanlar limitle.

Kullanım: python tani_secilim.py <çıktı adı> (yapılandırmalar aşağıdaki listeden).
"""
import json
import sys

import numpy as np
import pandas as pd

from grafik_analiz.research.data import load
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies import t2_limit_gun_ici as lg

assert PROTOCOL_VERSION == "2"

CONFIGS = json.loads(open(sys.argv[1]).read()) if len(sys.argv) > 1 else []


def episodes(df, p):
    tgt, lim, orders, exits, posv = lg.leg_orders(df, p)
    o = df["open"].to_numpy(float)
    n = len(df)
    H = int(p.get("H", 12))
    eps = {}
    for (j, side, lp, filled, px, mkt, eb) in orders:
        e = eps.setdefault(eb, {"side": side, "filled": False, "j": None, "px": None, "mkt": False})
        if filled and not e["filled"]:
            e.update(filled=True, j=j, px=px, mkt=mkt)
    rows = []
    for eb, e in eps.items():
        a = eb + 1
        if a + H >= n:
            continue
        r_mkt = e["side"] * (o[a + H] / o[a] - 1.0)
        r_lim = np.nan
        if e["filled"]:
            jf = e["j"]
            if jf + H >= n:
                continue
            r_lim = e["side"] * (o[jf + H] / e["px"] - 1.0)
        rows.append({"bas": df.index[eb], "dolu": e["filled"], "piyasa_emri": e["mkt"], "r_mkt": r_mkt, "r_lim": r_lim})
    return pd.DataFrame(rows)


def main():
    out = []
    for name, interval, p in CONFIGS:
        parts = []
        for coin in lg.COINS:
            df = load(coin, interval, "futures", scope="dev")
            df = df[df.index < DEV_TRAIN_END]
            ep = episodes(df, p)
            ep["coin"] = coin
            parts.append(ep)
        ep = pd.concat(parts, ignore_index=True)
        f = ep[ep["dolu"]]
        m = ep[~ep["dolu"]]
        row = {
            "ad": name,
            "bolum": len(ep),
            "dolum_orani": float(ep["dolu"].mean()),
            "dolanlarda_piyasa_emri_payi": float(f["piyasa_emri"].mean()) if len(f) else np.nan,
            "piyasa_getiri_dolan_bps": float(f["r_mkt"].mean() * 1e4) if len(f) else np.nan,
            "piyasa_getiri_dolmayan_bps": float(m["r_mkt"].mean() * 1e4) if len(m) else np.nan,
            "piyasa_getiri_hepsi_bps": float(ep["r_mkt"].mean() * 1e4),
            "limit_getiri_dolan_bps": float(f["r_lim"].mean() * 1e4) if len(f) else np.nan,
            "toplam_brut_piyasa_hepsi": float(ep["r_mkt"].sum()),
            "toplam_brut_limit_dolan": float(f["r_lim"].sum()),
        }
        out.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return out


if __name__ == "__main__":
    main()
