"""Keşif 4 (yalnız dev_train): ay dönümü etkisinin ayrıntısı.

- Her ayın dönüm penceresi getirisinin dağılımı (medyan, isabet oranı, en iyi aylar çıkınca)
- Pencere sınırları yüzeyi: son a gün + ilk b gün (a,b = 1..6), ay başına bileşik pencere getirisi
- Alt dönemler: 2017-2020 ve 2021-2023
- Alternatif çapa: ayın son cuması (vadeli/opsiyon vadesi) çevresi
"""
import numpy as np
import pandas as pd

from ortak import COINS, bar_returns, train_frame, tstat

pd.set_option("display.width", 250)
cells = 0


def rel_day(idx):
    dom = idx.day
    dim = idx.days_in_month
    from_end = dom - dim - 1
    return np.where(dom <= 15, dom, from_end)  # 1..15 baştan, -1..-16 sondan


def window_returns(r, a, b):
    """Her ay dönümü için (son a gün + sonraki ayın ilk b günü) bileşik getiri."""
    rel = rel_day(r.index)
    m = ((rel >= -a) & (rel < 0)) | ((rel >= 1) & (rel <= b))
    # ay dönümü kimliği: sonraki ayın başlangıcı
    key = np.where(rel < 0, (r.index + pd.offsets.MonthBegin(1)).strftime("%Y-%m"), r.index.strftime("%Y-%m"))
    s = pd.Series(np.log1p(r.values[m]), index=key[m])
    g = s.groupby(level=0)
    out = g.sum()
    cnt = g.count()
    return np.expm1(out[cnt == a + b])


for market in ("spot", "futures"):
    for sym in COINS:
        df = train_frame(sym, "1d", market)
        if market == "futures":
            df = df[df.index >= "2020-01-01"]
        r = bar_returns(df)
        w = window_returns(r, 3, 3)
        srt = w.sort_values(ascending=False)
        print(f"\n== {market} {sym}: [-3,+3] ay dönümü sayısı {len(w)}; ort {w.mean()*100:.2f}%  medyan {w.median()*100:.2f}%  isabet {(w>0).mean():.2f}  "
              f"en iyi 3 çıkınca ort {srt.iloc[3:].mean()*100:.2f}%  en iyi 5: {', '.join(f'{k}:{v*100:.0f}%' for k,v in srt.head(5).items())}")
        # aynı uzunlukta rastgele olmayan karşılaştırma: ayın 'orta' 6 günü (gün 10..15)
        rel = rel_day(r.index)
        mid = r[(rel >= 10) & (rel <= 15)]
        print(f"   orta 6 gün (10-15) ort günlük {mid.mean()*1e4:.1f} bp; tüm günler {r.mean()*1e4:.1f} bp")
        # alt dönemler
        for lo, hi in [("2017", "2020"), ("2021", "2023")]:
            ww = w[(w.index >= lo) & (w.index <= hi + "-12")]
            rr = r[(r.index >= lo) & (r.index < str(int(hi) + 1))]
            if len(ww):
                print(f"   {lo}-{hi}: pencere ort {ww.mean()*100:.2f}% medyan {ww.median()*100:.2f}% isabet {(ww>0).mean():.2f} (n={len(ww)}); 6 günlük ortalama al-tut {((1+rr.mean())**6-1)*100:.2f}%")
        if sym != "SOLUSDT":
            print("   yüzey (ay başına ort pencere getirisi %, satır a=son gün sayısı, sütun b=ilk gün sayısı) | t-istatistiği (günlük fark)")
            rows = []
            for a in range(0, 7):
                row = []
                for b in range(0, 7):
                    if a + b == 0:
                        row.append("   .  ")
                        continue
                    ww = window_returns(r, a, b)
                    m = ((rel >= -a) & (rel < 0)) | ((rel >= 1) & (rel <= b))
                    x, o = r[m], r[~m]
                    t = (x.mean() - o.mean()) / np.sqrt(x.var() / len(x) + o.var() / len(o))
                    row.append(f"{ww.mean()*100:5.2f}/{t:4.1f}")
                    cells += 1
                rows.append(f"   a={a}: " + " ".join(row))
            print("\n".join(rows))

print("\n=== Ayın son cuması çapası (gün farkı -7..+7), ortalama günlük bp ===")
for sym in COINS[:2]:
    df = train_frame(sym, "1d", "spot")
    r = bar_returns(df)
    idx = r.index
    month_end = idx + pd.offsets.MonthEnd(0)
    # ayın son cuması
    lf = month_end - pd.to_timedelta((month_end.dayofweek - 4) % 7, unit="D")
    d1 = (idx - lf).days
    nxt_me = (idx + pd.offsets.MonthEnd(1))
    lf_prev = (idx - pd.offsets.MonthBegin(1)) + pd.offsets.MonthEnd(0)
    lf_prev = lf_prev - pd.to_timedelta((lf_prev.dayofweek - 4) % 7, unit="D")
    d2 = (idx - lf_prev).days
    d = np.where(np.abs(d1) <= np.abs(d2), d1, d2)
    s = pd.Series(r.values, index=d)
    g = s[(s.index >= -7) & (s.index <= 7)].groupby(level=0).mean() * 1e4
    print(sym, " ".join(f"{k:+d}:{v:5.1f}" for k, v in g.items()))
    cells += 15
print("\nincelenen hücre:", cells)
