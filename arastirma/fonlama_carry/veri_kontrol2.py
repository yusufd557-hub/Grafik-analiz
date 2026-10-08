"""Spot/vadeli bar hizası ve SOL'un 8 saat dışı fonlama kayıtları (yalnız dev_train)."""
import pandas as pd
from grafik_analiz.research import load, load_funding, DEV_TRAIN_END

for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    f = load_funding(c, "dev")
    f = f[f.index < DEV_TRAIN_END]
    print(c, "dakika/saniye != 0:", int(((f.index.minute != 0) | (f.index.second != 0)).sum()))
    for iv in ("1h", "4h"):
        s = load(c, iv, "spot", "dev"); s = s[s.index < DEV_TRAIN_END]
        fu = load(c, iv, "futures", "dev"); fu = fu[fu.index < DEV_TRAIN_END]
        start = fu.index.min()
        s2 = s[s.index >= start]
        print(f"  {iv}: spot-only bars {len(s2.index.difference(fu.index))}, fut-only bars {len(fu.index.difference(s2.index))}")
        full = pd.date_range(start, fu.index.max(), freq=iv.replace('h','h'))
        print(f"     fut missing vs grid {len(full.difference(fu.index))}, spot missing {len(full.difference(s2.index))}")
    if c == "SOLUSDT":
        d = f.index.to_series().diff()
        off = f[d < pd.Timedelta("8h")]
        print("  8 saatten kisa aralikli kayit donemleri:", off.index.min(), off.index.max())
        print(off.groupby(off.index.to_period("M")).size())
        # Bu kayitlarda oranlar
        print(off["funding_rate"].describe())
