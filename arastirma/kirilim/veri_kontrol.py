"""Veri kontrolü: yalnızca harness load() ile, scope='dev'. Getiri hesaplanmaz."""
from grafik_analiz.research import load, load_funding

for market in ("spot", "futures"):
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for iv in ("15m", "1h", "4h", "1d"):
            try:
                df = load(sym, iv, market, scope="dev")
                print(market, sym, iv, len(df), df.index[0], df.index[-1], df.index.tz)
            except Exception as e:
                print(market, sym, iv, "HATA", e)
for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    f = load_funding(sym, scope="dev")
    print("funding", sym, len(f), f.index[0], f.index[-1], f.columns.tolist())
df = load("BTCUSDT", "15m", "spot", scope="dev")
print(df.head(3))
print(df.columns.tolist())
