"""Veri kontrolü: yalnız dev_train penceresi (2024 öncesi) incelenir."""
import numpy as np
import pandas as pd
from grafik_analiz.research import load, load_funding, DEV_TRAIN_END

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
for c in COINS:
    f = load_funding(c, "dev")
    f = f[f.index < DEV_TRAIN_END]
    print(c, "funding", f.index.min(), f.index.max(), len(f), list(f.columns))
    d = f.index.to_series().diff().value_counts().head(4)
    print("  aralik:", dict(d))
    r = f["funding_rate"]
    print("  ort %.6f medyan %.6f std %.6f min %.5f max %.5f neg_oran %.3f" % (r.mean(), r.median(), r.std(), r.min(), r.max(), (r < 0).mean()))
    print("  yillik ort (x3x365):", (r.groupby(r.index.year).mean() * 3 * 365).round(4).to_dict())
    print("  yillik neg oran:", (r < 0).groupby(r.index.year).mean().round(3).to_dict())
    # Otokorelasyon
    print("  AC1 %.3f AC3 %.3f AC21 %.3f" % (r.autocorr(1), r.autocorr(3), r.autocorr(21)))
    print("  saat dagilimi:", f.index.hour.value_counts().to_dict())
    for m in ("spot", "futures"):
        for iv in ("1h", "4h", "1d"):
            df = load(c, iv, m, "dev")
            df = df[df.index < DEV_TRAIN_END]
            print(f"  {m} {iv}: {df.index.min()} .. {df.index.max()} n={len(df)}")
f = load_funding("BTCUSDT", "dev")
print(f.head())
