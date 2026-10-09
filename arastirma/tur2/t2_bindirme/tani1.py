"""Tanı 1 (yalnız eğitim, veri 31.12.2024'te kesik): deftere yazılmış birkaç yapılandırmanın yıllık işlem sayısı ve bacak dökümü."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd
from ortak import egitim_calistir
from tarama1 import FON, LB
from grafik_analiz.strategies.t2_bindirme import make_spec

K = [
    ("t2_bindirme_trendvol_yarim_4h_L10_h0.3_n30_b0.1_f7", "4h", dict(sinyal="trend_vol", bicim="yarim", lookbacks=LB["L10"], hedef_vol=0.3, vol_gun=30, bant=0.1, **FON["f7"])),
    ("t2_bindirme_trendvol_yarim_4h_L10_h0.4_n30_b0.1_f7", "4h", dict(sinyal="trend_vol", bicim="yarim", lookbacks=LB["L10"], hedef_vol=0.4, vol_gun=30, bant=0.1, **FON["f7"])),
    ("t2_bindirme_trend_yarim_4h_L15_b0.15_f7", "4h", dict(sinyal="trend", bicim="yarim", lookbacks=(15, 30, 60), bant=0.15, **FON["f7"])),
    ("t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7", "4h", dict(sinyal="trend_vol", bicim="tam", lookbacks=LB["L10"], hedef_vol=0.3, vol_gun=30, bant=0.1, **FON["f7"])),
]
for name, iv, kw in K:
    res, _ = egitim_calistir(make_spec(name, iv, **kw))
    t = res.trades
    t = t[t.entry_time >= pd.Timestamp("2020-01-01", tz="UTC")]
    by = t.groupby([t.entry_time.dt.year, "leg"]).size().unstack(fill_value=0)
    print(name.replace("t2_bindirme_", ""))
    print(by.assign(toplam=by.sum(axis=1)).to_string())
    # Yarı yıllık toplam (21 aylık pencerede beklenen sayı için)
    h = t.groupby(t.entry_time.dt.to_period("Q")).size()
    print("çeyrek başına işlem: min", h.min(), "medyan", h.median(), "maks", h.max())
    print()
