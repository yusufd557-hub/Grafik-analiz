"""dev_train tarama sonuçlarının grup özeti (tarama1, tarama2, tarama3 CSV'lerinden)."""
import json
import pandas as pd
from pathlib import Path

K = Path(__file__).resolve().parent
d = pd.concat([pd.read_csv(K / f) for f in ("tarama1.csv", "tarama2_carry.csv", "tarama2_yonlu.csv", "tarama3_carry.csv", "tarama3_kaplama.csv")], ignore_index=True)
p = d.params.apply(json.loads)
print("benzersiz yapilandirma:", d.ad.nunique(), "satir:", len(d))


def grup(r):
    q = json.loads(r.params)
    if r.kind == "carry":
        if q["n"] == 0:
            return "carry sürekli"
        g, c = q["giris"], q["cikis"]
        if abs(g - 1e-4) < 1e-12 or abs(c - 1e-4) < 1e-12 or abs(g - 2e-4) < 1e-12 and abs(c - 1e-4) < 1e-12:
            t = "eşik 1e-4 kütle noktasında"
        elif g == 0.0:
            t = "giriş 0"
        elif g < 1e-4:
            t = "giriş < 1e-4"
        else:
            t = "giriş > 1e-4"
        return f"carry {t}" + (" +son_neg" if q["son_neg"] else "")
    if r.kind == "yonlu":
        if q["olcek"] == "yuzdelik":
            return f"yönlü yüzdelik iki yön, filtre {q['filtre']}"
        return f"yönlü {q['yon']}, filtre {q['filtre']}"
    if q["ust"] >= 1:
        return "kaplama kontrol (yalnız trend)"
    return f"kaplama, filtre {q['filtre']}, uzun_poz {q['uzun_poz']}"


d["grup"] = d.apply(grup, axis=1)
rows = []
for (g, u), x in d.groupby(["grup", "universe"], sort=True):
    rows.append({"grup": g, "evren": u, "n": len(x), "net>0": int((x.getiri > 0).sum()),
                 "S_min": x.sharpe.min(), "S_med": x.sharpe.median(), "S_max": x.sharpe.max(),
                 "2x>0": int((x.getiri_2x > 0).sum()), "DD_med": x.maxdd.median(), "getiri_med": x.getiri.median()})
o = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(o.round(3).to_string(index=False))
o.to_csv(K / "ozet_dev_train.csv", index=False)
