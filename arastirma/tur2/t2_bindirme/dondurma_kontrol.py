"""Dondurma kontrolü (dev_valid değerlendirmesinden önce):
1. Dondurulan spec parametrelerinin defterdeki dev_train satırlarıyla birebir aynı olduğu.
2. assert_causal: varsayılan kesimler (0,55 / 0,8 / 0,97) + ek kesimler; portföyde ayrıca
   ML aylık yeniden eğitiminden hemen sonraya denk gelen kesim (2024-03-01 02:00 UTC).
Performans ölçüsü hesaplamaz.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import assert_causal, load_data
from grafik_analiz.research.ledger import _clean, ledger_path
from grafik_analiz.strategies.t2_bindirme import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"
defter = {}
for line in ledger_path(FAMILY).read_text(encoding="utf-8").splitlines():
    e = json.loads(line)
    if e["pencere"] == "dev_train" and e["maliyet_kat"] == 1.0:
        defter.setdefault(e["strateji"], []).append(e["parametreler"])

secim = sys.argv[1:] or None
for s in specs():
    if secim and not any(a in s.name for a in secim):
        continue
    p = _clean({"interval": s.interval, "legs": [list(l) for l in s.legs], **s.params})
    esit = any(json.dumps(p, sort_keys=True) == json.dumps(q, sort_keys=True) for q in defter.get(s.name, []))
    print(f"{s.name}: defterde aynı parametre: {esit}", flush=True)
    t = time.time()
    assert_causal(s)
    print(f"  assert_causal varsayılan: GEÇTİ ({time.time() - t:.0f}s)", flush=True)
    ek = (0.3, 0.9, 0.995)
    if s.name.startswith("t2_bindirme_portfoy"):
        data, _ = load_data(s, "dev")
        idx = data[s.legs[0]].index
        pos = idx.searchsorted(pd.Timestamp("2024-03-01 02:00", tz="UTC"))
        ek = ek + ((pos + 0.5) / len(idx),)
    t = time.time()
    assert_causal(s, fractions=ek)
    print(f"  assert_causal ek kesimler {tuple(round(x, 4) for x in ek)}: GEÇTİ ({time.time() - t:.0f}s)", flush=True)
print("BITTI", flush=True)
