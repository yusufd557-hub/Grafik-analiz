"""Aşama 3: kısa listedeki bölgelerin komşu kontrolü (yalnız dev_train, 1× ve 2×)."""
from ortak import train_eval

jobs = []
def add(tag, iv, market, **p):
    jobs.append((tag, iv, market, p))

UK = ["ucgen", "kama"]
# F1: 4h vadeli alım üçgen+kama + trend
b = dict(yontem="grafik", tipler=UK, yon="uzun", cikis="hedef")
for tn in (100, 400):
    add("3F1", "4h", "futures", **b, trend_n=tn)
add("3F1", "4h", "futures", **{**b, "hedef_k": 1.5}, trend_n=200)
add("3F1", "4h", "futures", **b, trend_n=200, hacim_k=1.5)
add("3F1", "4h", "futures", **{**b, "cikis": "stop_sure"}, trend_n=200)
add("3F1", "4h", "futures", **b, trend_n=200, olcekler=[2.0, 3.0, 4.0])
add("3F1", "4h", "futures", **{**b, "tipler": "ucgen"}, trend_n=200)
add("3F1", "4h", "futures", **{**b, "tipler": "kama"}, trend_n=200)
add("3F1", "4h", "futures", **{**b, "tipler": UK + ["dikdortgen"]}, trend_n=200)
# F2: 4h vadeli iki yön üçgen+kama + hacim
b = dict(yontem="grafik", tipler=UK, yon="iki", cikis="hedef")
for hk in (1.25, 2.0):
    add("3F2", "4h", "futures", **b, hacim_k=hk)
add("3F2", "4h", "futures", **b, hacim_k=1.5, trend_n=200)
add("3F2", "4h", "futures", **{**b, "yon": "kisa"}, hacim_k=1.5)
add("3F2", "4h", "futures", **{**b, "hedef_k": 1.5}, hacim_k=1.5)
# F3: 4h vadeli alım bütün tipler + trend + kısa tutma
b = dict(yontem="grafik", tipler="hepsi", yon="uzun", cikis="sure")
for mb in (5, 15):
    add("3F3", "4h", "futures", **b, max_bar=mb, trend_n=200)
for tn in (100, 400):
    add("3F3", "4h", "futures", **b, max_bar=10, trend_n=tn)
add("3F3", "4h", "futures", **b, max_bar=10, trend_n=200, hacim_k=1.5)
add("3F3", "4h", "futures", **{**b, "tipler": UK}, max_bar=10, trend_n=200)
add("3F3", "4h", "spot", **b, max_bar=15, trend_n=200)
add("3F3", "4h", "futures", **{**b, "yon": "iki"}, max_bar=5, trend_n=200)
# F4: 1d vadeli iki yön bütün tipler, ölçekler
b = dict(yontem="grafik", tipler="hepsi", yon="iki", cikis="hedef")
for sc in ([2.0, 3.0], [3.0], [3.0, 4.0]):
    add("3F4", "1d", "futures", **b, olcekler=sc)
add("3F4", "1d", "futures", **{**b, "hedef_k": 1.5}, olcekler=[2.0, 3.0, 4.0])
add("3F4", "1d", "futures", **{**b, "cikis": "stop_sure"}, olcekler=[2.0, 3.0, 4.0])
add("3F4", "1d", "futures", **{**b, "yon": "uzun"}, olcekler=[2.0, 3.0, 4.0])
add("3F4", "1d", "spot", **{**b, "yon": "uzun"}, olcekler=[2.0, 3.0, 4.0])
add("3F4", "1d", "futures", **{**b, "tipler": UK}, olcekler=[2.0, 3.0, 4.0])
# F5: 1d marubozu ATR çıkışı
b = dict(yontem="mum", tipler="marubozu", yon="iki", cikis="atr")
add("3F5", "1d", "futures", **b, stop_k=1.5, hedef_atr=4.0, tutma=20)
add("3F5", "1d", "futures", **b, stop_k=3.0, hedef_atr=4.0, tutma=20)
add("3F5", "1d", "futures", **b, stop_k=2.0, hedef_atr=3.0, tutma=20)
add("3F5", "1d", "futures", **b, stop_k=2.0, hedef_atr=6.0, tutma=20)
add("3F5", "1d", "futures", **b, stop_k=2.0, hedef_atr=4.0, tutma=10)
add("3F5", "1d", "futures", **b, stop_k=2.0, hedef_atr=4.0, tutma=30)
add("3F5", "1d", "futures", **{**b, "tipler": ["marubozu", "asker"]}, stop_k=2.0, hedef_atr=4.0, tutma=20)

print("iş sayısı", len(jobs), flush=True)
for i, (tag, iv, market, p) in enumerate(jobs):
    r = train_eval(iv, market, "PORT3", p, tag)
    print(i, tag, r["name"], f"ret1={r['ret1']:.3f} sh1={r['sharpe1']:.3f} ret2={r['ret2']:.3f} sh2={r['sharpe2']:.3f} mdd={r['mdd1']:.3f} n={r['trades']} exp={r['exposure']:.2f}", flush=True)
