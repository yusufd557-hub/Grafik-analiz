"""Dondurulan yapılandırmalar için dev_valid öncesi kontroller (performans hesaplamaz):
1) ad ve parametreler defterdeki dev_train satırıyla birebir aynı mı,
2) assert_causal (varsayılan kesimler + ek kesimler)."""
import json

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import assert_causal
from grafik_analiz.research.ledger import _clean, ledger_path
from grafik_analiz.strategies.t2_cift import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"
rows = [json.loads(l) for l in ledger_path(FAMILY).read_text(encoding="utf-8").splitlines() if l.strip()]
for spec in specs():
    p = _clean({"interval": spec.interval, "legs": [list(l) for l in spec.legs], **spec.params})
    hits = [r for r in rows if r["strateji"] == spec.name and r["pencere"] == "dev_train" and r["parametreler"] == p]
    print(spec.name, "defter eşleşmesi:", len(hits), "satır", flush=True)
    assert hits, "defterde yok"
    assert_causal(spec)
    print("  assert_causal (0.55, 0.8, 0.97): geçti", flush=True)
    assert_causal(spec, fractions=(0.3, 0.5, 0.65, 0.75, 0.9, 0.99))
    print("  assert_causal (0.3, 0.5, 0.65, 0.75, 0.9, 0.99): geçti", flush=True)
