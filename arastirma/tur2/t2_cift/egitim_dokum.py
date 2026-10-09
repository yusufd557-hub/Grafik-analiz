"""Dondurulan yapılandırmaların eğitim içi dökümü (veri 31.12.2024'te kesilir; dev_valid hesaba girmez)
ve tarama 1 (klasik düzey z) yapılandırmalarında fonlamanın payı (tarama1.csv'den, yalnız eğitim)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from ortak import egitim_dokumu  # noqa: E402

from grafik_analiz.strategies.t2_cift import FROZEN  # noqa: E402

out = {}
for kod, (name, params, _) in zip("BCD", FROZEN):
    d = egitim_dokumu("1h", dict(params))
    out[kod] = d
    print(kod, name)
    print("  yıllık net:", d["yillik"])
    print("  yıllık brüt:", d["yillik_brut_toplam"])
    print("  yıllık maliyet:", d["yillik_maliyet"])
    print("  yıllık fonlama (ödenen +):", d["yillik_fonlama"])
    print("  toplam brüt / maliyet / fonlama:", round(d["brut_toplam"], 4), round(d["maliyet_toplam"], 4), round(d["fonlama_toplam"], 4))
    print("  bacak:", json.dumps(d["bacak"]), flush=True)
Path(Path(__file__).parent / "egitim_dokum.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")

t1 = pd.read_csv(Path(__file__).parent / "tarama1.csv")
t1["cift"] = t1["ad"].str.extract(r"_(ETHBTC|SOLBTC|SOLETH)_")
t1["fonlama_kazanc"] = -t1["fonlama"]
print("\nTarama 1 (klasik düzey z, eğitim): çift başına ortalama net getiri, fonlama kazancı (alınan +), maliyet")
print(t1.groupby(["interval", "cift"])[["ret", "fonlama_kazanc", "maliyet"]].mean().round(3).to_string())
