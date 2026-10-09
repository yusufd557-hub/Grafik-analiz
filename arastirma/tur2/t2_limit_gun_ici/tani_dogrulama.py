"""dev_valid değerlendirmesinden SONRA betimleyici tanı (hiçbir parametre değişmedi, deftere yazılmaz):
dondurulan limitli yapılandırmalarda dolum oranı ve bölüm düzeyinde ters seçilim, dev_train ve dev_valid ayrı."""
import json

import numpy as np
import pandas as pd

from grafik_analiz.research.data import load
from grafik_analiz.research.metrics import deflated_sharpe
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies import t2_limit_gun_ici as lg

assert PROTOCOL_VERSION == "2"


def episodes(df, p):
    tgt, lim, orders, exits, posv = lg.leg_orders(df, p)
    o = df["open"].to_numpy(float)
    n = len(df)
    H = int(p.get("H", 12))
    eps = {}
    for (j, side, lp, filled, px, mkt, eb) in orders:
        e = eps.setdefault(eb, {"side": side, "filled": False, "j": None, "px": None, "mkt": False, "emir": 0})
        e["emir"] += 1
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
            if e["j"] + H >= n:
                continue
            r_lim = e["side"] * (o[e["j"] + H] / e["px"] - 1.0)
        rows.append({"bas": df.index[eb], "dolu": e["filled"], "emir": e["emir"], "r_mkt": r_mkt, "r_lim": r_lim})
    return pd.DataFrame(rows)


out = []
for spec in lg.specs():
    if spec.params.get("giris") == "piyasa":
        continue
    parts = []
    for c in lg.COINS:
        df = load(c, spec.interval, "futures", scope="dev")
        ep = episodes(df, spec.params)
        ep["coin"] = c
        parts.append(ep)
    ep = pd.concat(parts, ignore_index=True)
    for w, mask in (("dev_train", ep["bas"] < DEV_TRAIN_END), ("dev_valid", ep["bas"] >= DEV_TRAIN_END)):
        x = ep[mask]
        f, m = x[x["dolu"]], x[~x["dolu"]]
        row = {
            "ad": spec.name, "pencere": w, "bolum": int(len(x)), "emir": int(x["emir"].sum()),
            "dolum_orani_bolum": float(x["dolu"].mean()) if len(x) else None,
            "dolum_orani_emir": float(len(f) / x["emir"].sum()) if len(x) else None,
            "piyasa_getiri_dolan_bps": float(f["r_mkt"].mean() * 1e4) if len(f) else None,
            "piyasa_getiri_dolmayan_bps": float(m["r_mkt"].mean() * 1e4) if len(m) else None,
            "limit_getiri_dolan_bps": float(f["r_lim"].mean() * 1e4) if len(f) else None,
            "toplam_brut_piyasa_hepsi": float(x["r_mkt"].sum()),
            "toplam_brut_limit_dolan": float(f["r_lim"].sum()),
        }
        out.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

# Bağlam: deneme sayısı 1 kabul edilirse (çoklu deneme düzeltmesi yok) olasılıksal Sharpe
res = json.load(open("dogrulama_sonuc.json", encoding="utf-8"))
for r in res["yapilandirmalar"]:
    v = r["sonuclar"]["dev_valid"]["1.0"]
    psr = deflated_sharpe(v["sharpe"], r["dev_valid_gun_sayisi"], 1, 0.0, v["skew"], v["kurtosis"])
    print(f"PSR(N=1) {r['ad']}: {psr:.3f}")
json.dump(out, open("tani_dogrulama.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
