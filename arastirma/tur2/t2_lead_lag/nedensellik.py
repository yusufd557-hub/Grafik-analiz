"""Dondurulan yapılandırmalar için ileri bakış denetimi (assert_causal, varsayılan ve ek kesimler)."""
import time

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import assert_causal
from grafik_analiz.strategies.t2_lead_lag import specs

assert protocol.PROTOCOL_VERSION == "2"
for spec in specs():
    t = time.time()
    assert_causal(spec)
    assert_causal(spec, fractions=(0.3, 0.62, 0.9))
    print(f"GEÇTİ {spec.name} ({time.time() - t:.0f}s)", flush=True)
