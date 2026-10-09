"""Tanı 2 (yalnız eğitim, veri 31.12.2024'te kesik): alt dönem alfa şartlarını geçen tarama 1/3
yapılandırmalarının 2023 ve 2024 işlem sayıları."""
import ast
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
from ortak import egitim_calistir
from grafik_analiz.strategies.t2_bindirme import make_spec

KEYS = ("sinyal", "bicim", "lookbacks", "hedef_vol", "vol_gun", "bant", "fon_n", "fon_giris", "fon_cikis", "sabit")
d = pd.concat([pd.read_csv("tarama1.csv"), pd.read_csv("tarama3.csv")]).drop_duplicates("ad")
x = d[(d.alfa_20_23 > 0) & (d.alfa_24 > 0) & (d.ret2 > 0)].sort_values("alfa_t", ascending=False)
rows = []
for _, r in x.iterrows():
    kw = {}
    for k in KEYS:
        if k in r and pd.notna(r[k]):
            v = r[k]
            try:
                v = ast.literal_eval(v) if isinstance(v, str) and k not in ("sinyal", "bicim") else v
            except (ValueError, SyntaxError):
                pass
            kw[k] = v
    res, _ = egitim_calistir(make_spec(r["ad"], r["interval"], **kw))
    t = res.trades
    y = t.entry_time.dt.year.value_counts()
    rows.append({"ad": r["ad"].replace("t2_bindirme_", ""), "alfa_t": r["alfa_t"], "i2022": int(y.get(2022, 0)), "i2023": int(y.get(2023, 0)), "i2024": int(y.get(2024, 0))})
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv("tani2.csv", index=False)
