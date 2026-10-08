"""Aşama 2: aşama 1'in umut veren bölgelerinde daraltma (yalnız dev_train, 1× ve 2×)."""
from ortak import train_eval

M3 = [("futures", "iki"), ("futures", "uzun"), ("spot", "uzun")]
jobs = []

def add(tag, iv, market, **p):
    jobs.append((tag, iv, market, p))

EXITS = [
    {"cikis": "hedef"},
    {"cikis": "hedef", "hedef_k": 1.5},
    {"cikis": "hedef", "hedef_k": 2.0},
    {"cikis": "stop_sure"},
    {"cikis": "sure", "max_bar": 20},
]
# A) 4h konsolidasyon formasyonları
for tip in ("ucgen", "kama", ["ucgen", "kama"]):
    for market, yon in M3:
        for ex in EXITS:
            add("2A", "4h", market, yontem="grafik", tipler=tip, yon=yon, **ex)
for market, yon in M3:
    base = dict(yontem="grafik", tipler=["ucgen", "kama"], yon=yon, cikis="hedef")
    add("2A", "4h", market, **base, trend_n=200)
    add("2A", "4h", market, **base, hacim_k=1.5)
    add("2A", "4h", market, **base, egilim_uyumu=True)
    for sc in ([2.0], [4.0], [2.0, 3.0, 4.0], [1.5, 3.0]):
        add("2A", "4h", market, **base, olcekler=sc)
# B) 4h bütün tipler + trend filtresi
for market, yon in M3:
    for ex in ({"cikis": "sure", "max_bar": 10}, {"cikis": "sure", "max_bar": 20}, {"cikis": "sure", "max_bar": 40},
               {"cikis": "stop_sure"}, {"cikis": "hedef"}, {"cikis": "hedef", "hedef_k": 2.0}):
        add("2B", "4h", market, yontem="grafik", tipler="hepsi", yon=yon, trend_n=200, **ex)
    for tn in (100, 400):
        add("2B", "4h", market, yontem="grafik", tipler="hepsi", yon=yon, trend_n=tn, cikis="sure", max_bar=20)
    add("2B", "4h", market, yontem="grafik", tipler="hepsi", yon=yon, trend_n=200, hacim_k=1.5, cikis="sure", max_bar=20)
# C) 1d bütün tipler
for market, yon in M3:
    for ex in ({"cikis": "hedef", "hedef_k": 0.5}, {"cikis": "hedef"}, {"cikis": "hedef", "hedef_k": 1.5}, {"cikis": "hedef", "hedef_k": 2.0},
               {"cikis": "stop_sure"}, {"cikis": "sure", "max_bar": 10}, {"cikis": "sure", "max_bar": 20}, {"cikis": "sure", "max_bar": 40}):
        add("2C", "1d", market, yontem="grafik", tipler="hepsi", yon=yon, **ex)
for ex in ({"cikis": "hedef"}, {"cikis": "sure", "max_bar": 20}):
    for sc in ([1.5, 3.0], [2.0, 3.0, 4.0], [1.5, 2.0, 3.0, 4.0]):
        add("2C", "1d", "futures", yontem="grafik", tipler="hepsi", yon="iki", olcekler=sc, **ex)
    add("2C", "1d", "futures", yontem="grafik", tipler="hepsi", yon="iki", hacim_k=1.5, **ex)
    add("2C", "1d", "futures", yontem="grafik", tipler="hepsi", yon="iki", egilim_uyumu=True, **ex)
# D) 1d marubozu
for market, yon in M3:
    for ex in ({"cikis": "sure", "tutma": 5}, {"cikis": "sure", "tutma": 10}, {"cikis": "sure", "tutma": 20},
               {"cikis": "atr", "stop_k": 2.0, "hedef_atr": 4.0, "tutma": 20}):
        add("2D", "1d", market, yontem="mum", tipler="marubozu", yon=yon, **ex)

print("iş sayısı", len(jobs), flush=True)
for i, (tag, iv, market, p) in enumerate(jobs):
    r = train_eval(iv, market, "PORT3", p, tag)
    print(i, tag, r["name"], f"ret1={r['ret1']:.3f} sh1={r['sharpe1']} ret2={r['ret2']:.3f} sh2={r['sharpe2']} n={r['trades']} exp={r['exposure']} t={r['sec']}", flush=True)
