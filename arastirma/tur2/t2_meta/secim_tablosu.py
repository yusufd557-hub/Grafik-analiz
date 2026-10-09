"""Dondurma seçimi için dev_train tablosu (tarama CSV'lerinden; yalnız dev_train)."""
import json
from pathlib import Path

import pandas as pd

K = Path(__file__).resolve().parent
PRIM_KEYS = ("birincil", "n", "k", "z", "fz", "hizli", "yavas", "cikis", "tp", "sl", "H", "iz_k", "yon", "topluluk")
import sys
sys.path.insert(0, str(K))
from grafik_analiz.strategies.t2_meta import DEFAULTS  # noqa: E402

frames = [pd.read_csv(f) for f in sorted(K.glob("tarama*.csv"))]
df = pd.concat(frames, ignore_index=True)
df["p"] = df["params"].map(lambda s: {**DEFAULTS, **json.loads(s)})


def prim_key(row):
    p = row["p"]
    keys = [k for k in PRIM_KEYS]
    kinds = p["birincil"].split("+")
    rel = {"birincil", "cikis", "H", "yon", "topluluk"}
    if "kanal" in kinds: rel.add("n")
    if "donus" in kinds: rel |= {"k", "z"}
    if "fonlama" in kinds: rel.add("fz")
    if "ema" in kinds: rel |= {"hizli", "yavas"}
    rel |= {"tp", "sl"} if p["cikis"] == "bariyer" else {"iz_k"}
    return (row["aralik"],) + tuple((k, p[k]) for k in keys if k in rel)


df["prim"] = df.apply(prim_key, axis=1)
df["model"] = df["p"].map(lambda p: p["model"])
x1 = df[df["maliyet"] == 1.0].drop_duplicates("isim", keep="last").copy()
x2 = df[df["maliyet"] == 2.0].drop_duplicates("isim", keep="last").set_index("isim")
base = x1[x1["model"] == "hepsi"].groupby("prim")["sharpe"].max()
x1["hepsi_sharpe"] = x1["prim"].map(base)
x1["ret2x"] = x1["isim"].map(x2["total_return"])
x1["grup"] = x1.apply(lambda r: f"{r['aralik']} {r['p']['birincil']}", axis=1)
cols = ["isim", "grup", "total_return", "ret2x", "sharpe", "hepsi_sharpe", "max_drawdown", "trades", "alfa", "beta", "alfa_t"]
meta = x1[x1["model"] != "hepsi"]
ok = meta[(meta["total_return"] > 0) & (meta["alfa"] > 0) & (meta["trades"] >= 60) & (meta["sharpe"] > meta["hepsi_sharpe"].fillna(-9))]
ok = ok.sort_values(["alfa_t", "sharpe"], ascending=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 95)
print("toplam 1x yapılandırma:", len(x1), " meta:", len(meta), " uygun (2x hariç):", len(ok))
for g, sub in ok.groupby("grup", sort=False):
    print(f"\n### {g}")
    print(sub[cols].head(8).round(3).to_string(index=False))
