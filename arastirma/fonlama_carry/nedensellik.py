"""Dondurulan yapılandırmalar için ileri bakış denetimi (assert_causal): varsayılan ve ek kesim noktaları.
Performans ölçüsü hesaplanmaz."""
from grafik_analiz.research import assert_causal
from grafik_analiz.strategies.fonlama_carry import specs

for spec in specs():
    assert_causal(spec)
    assert_causal(spec, fractions=(0.2, 0.35, 0.5, 0.62, 0.7, 0.75, 0.85, 0.9, 0.95, 0.99))
    print("GECTI", spec.name)
