"""Veri kapsamı kontrolü (yalnız scope='dev')."""
from grafik_analiz.research import load, load_funding

for market in ("spot", "futures"):
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for iv in ("1d", "4h", "1h"):
            try:
                df = load(sym, iv, market, scope="dev")
                print(market, sym, iv, df.index[0], df.index[-1], len(df), df.index.tz)
            except Exception as e:
                print(market, sym, iv, "HATA", e)
for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    f = load_funding(sym, scope="dev")
    print("funding", sym, f.index[0], f.index[-1], len(f), f["funding_rate"].describe().to_dict())
df = load("BTCUSDT", "1d", "spot")
print(df.head(3)); print(df.columns.tolist())
