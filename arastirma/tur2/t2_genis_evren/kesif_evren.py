"""Evren tablosunun yapısı (performans bilgisi yok): üye sayıları, veri aralıkları."""
import pandas as pd
from grafik_analiz.research.data import load_universe, available_symbols, load, load_funding

u = load_universe("dev")
print(u.head())
print("aylar:", u["ay"].min(), u["ay"].max(), u["ay"].nunique())
print("toplam farklı sembol:", u["sembol"].nunique())
tr = u[u["ay"] < "2025-01-01"]
print("dev_train farklı sembol:", tr["sembol"].nunique())
print("aylık üye sayısı:", u.groupby("ay").size().describe())
a4 = set(available_symbols("futures", "4h")); a1 = set(available_symbols("futures", "1d"))
syms = sorted(u["sembol"].unique())
print("4h eksik:", [s for s in syms if s not in a4])
print("1d eksik:", [s for s in syms if s not in a1])
# Veri bitişleri (delist) — ay içi
rows = []
for s in syms:
    df = load(s, "4h", "futures")
    months = u.loc[u.sembol == s, "ay"]
    rows.append((s, df.index[0], df.index[-1], months.min(), months.max(), len(months)))
d = pd.DataFrame(rows, columns=["s", "ilk", "son", "ay_ilk", "ay_son", "n_ay"])
end = d["son"].max()
erken = d[d["son"] < end - pd.Timedelta(days=1)]
print("veri dev sonundan önce biten:", len(erken))
# evrendeyken biten: son bar, son evren ayının içinde
ic = erken[erken["son"] < erken["ay_son"] + pd.offsets.MonthBegin(1)]
print(ic.to_string())
print("ilk ay listesi:", u[u.ay == u.ay.min()]["sembol"].tolist())
