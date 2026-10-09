"""Dondurulan yapılandırmalar için ileri bakış denetimi (assert_causal) ve defterde
aynı parametrelerle dev_train satırı bulunduğunun kontrolü. dev_valid ölçüsü üretmez."""
import json

from grafik_analiz.research.evaluate import assert_causal
from grafik_analiz.research.ledger import ledger_path
from grafik_analiz.research.protocol import PROTOCOL_VERSION
from grafik_analiz.strategies.t2_emir_akisi import FAMILY, specs

assert PROTOCOL_VERSION == "2"
rows = [json.loads(l) for l in ledger_path(FAMILY).open(encoding="utf-8")]
assert all(r["pencere"] == "dev_train" for r in rows), "defterde dev_valid satırı var"
for spec in specs():
    p = json.loads(json.dumps({"interval": spec.interval, "legs": [list(l) for l in spec.legs], **spec.params}))
    same = [r for r in rows if r["parametreler"] == p and r["maliyet_kat"] == 1.0]
    assert same, f"{spec.name}: defterde aynı parametreli dev_train satırı yok"
    sh = same[0]["olcu"].get("sharpe")
    assert_causal(spec)
    assert_causal(spec, fractions=(0.3, 0.62, 0.9, 0.995))
    print(f"{spec.name}: assert_causal geçti (7 kesim); defterde {len(same)} eş dev_train satırı, Sharpe {sh}", flush=True)
