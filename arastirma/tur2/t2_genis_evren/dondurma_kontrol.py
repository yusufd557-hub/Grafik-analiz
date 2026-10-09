"""Dondurulan yapılandırmalar için ileri bakış denetimi (dev_valid'e bakmadan önce).

`assert_causal` varsayılan kesimlerle (0.55, 0.8, 0.97) ve ek kesimlerle
(0.3, 0.45, 0.65, 0.9, 0.99) çalıştırılır. Ayrıca her spec'in dev_train
sonucunun deftere yazılmış arama sonucuyla aynı olduğu yeniden üretilerek
denetlenir (record=False; deftere yazılmaz, dev_valid hesaplanmaz).
"""
import json
import time

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import assert_causal, evaluate
from grafik_analiz.research.ledger import trials
from grafik_analiz.strategies.t2_genis_evren import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"

tr = trials(FAMILY)
tr = tr[(tr["pencere"] == "dev_train") & (tr["maliyet_kat"] == 1.0)]
for s in specs():
    t0 = time.time()
    assert_causal(s)
    assert_causal(s, fractions=(0.3, 0.45, 0.65, 0.9, 0.99))
    key = json.dumps({"interval": s.interval, "legs": [list(l) for l in s.legs], **s.params}, sort_keys=True)
    rows = tr[[json.dumps(p, sort_keys=True) == key for p in tr["parametreler"]]]
    res = evaluate(s, windows=("dev_train",), cost_multipliers=(1.0,), record=False)
    m = res["dev_train"][1.0]
    led = rows.iloc[0]["olcu"] if len(rows) else None
    same = led is not None and abs(led["total_return"] - m["total_return"]) < 1e-5 and abs(led["sharpe"] - m["sharpe"]) < 1e-4
    print(f"{s.name}: assert_causal GEÇTİ (8 kesim) | defterde {len(rows)} satır | dev_train yeniden üretim "
          f"{m['total_return']:+.6f} / defter {led['total_return'] if led else None} -> {'AYNI' if same else 'FARKLI'} "
          f"({time.time()-t0:.0f}s)", flush=True)
print("BITTI", flush=True)
