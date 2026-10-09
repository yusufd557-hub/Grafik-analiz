"""dev_valid SONRASI betimleyici döküm (yeniden ayar YOK; yalnız dondurulmuş spec'ler, aynı veri).
Bacak katkıları, fonlama/maliyet, yarım yıllık getiriler ve al-tut kıyası."""
import numpy as np
import pandas as pd
from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import benchmark_daily, run
from grafik_analiz.research.metrics import daily_returns, window
from grafik_analiz.strategies.t2_bindirme import specs

V0, V1 = protocol.PERIODS["dev_valid"]
dummy = type("S", (), {"legs": (("futures", "BTCUSDT"),)})()
b = benchmark_daily(dummy, "dev")
b = b[(b.index >= V0) & (b.index < V1)]
parcalar = [("2025-01-01", "2025-07-01"), ("2025-07-01", "2026-01-01"), ("2026-01-01", "2026-10-01")]
for s in specs():
    if "portfoy" in s.name:
        continue
    r = run(s, "dev", 1.0)
    w = s.leg_weights()
    print(s.name)
    for leg, lr in r.legs.items():
        net = window(lr.net, V0, V1) * w[leg]
        fund = window(lr.funding, V0, V1).sum() * w[leg]
        cost = window(lr.cost, V0, V1).sum() * w[leg]
        pos = window(lr.position, V0, V1)
        print(f"  {leg}: net katkı (toplam) {net.sum():+.4f}  fonlama {-fund:+.4f} (+ = gelir)  maliyet {cost:.4f}  ort. pozisyon {pos.mean():+.3f}")
    d = daily_returns(window(r.returns, V0, V1))
    for a, z in parcalar:
        a, z = pd.Timestamp(a, tz="UTC"), pd.Timestamp(z, tz="UTC")
        ds = d[(d.index >= a) & (d.index < z)]
        bs = b[(b.index >= a) & (b.index < z)]
        print(f"  {a.date()}–{z.date()}: strateji {(1 + ds).prod() - 1:+.4f}  al-tut (vadeli) {(1 + bs).prod() - 1:+.4f}")
    srt = d.sort_values(ascending=False)
    print(f"  en iyi 5 gün toplamı {srt.iloc[:5].sum():+.4f}; en iyi 10 gün çıkarılınca bileşik getiri {(1 + srt.iloc[10:]).prod() - 1:+.4f}")
    # Maruziyet: coin başına net (spot + vadeli) ağırlıklı pozisyon ortalaması
    net_exp = {}
    for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        e = 0
        for leg, lr in r.legs.items():
            if leg[1] == c:
                e = e + window(lr.position, V0, V1).reindex(window(r.returns, V0, V1).index).ffill().fillna(0) * w[leg]
        net_exp[c] = float(np.mean(e))
    print(f"  ortalama net maruziyet (sermaye payı): {net_exp}")
