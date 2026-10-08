"""Dondurulan her yapılandırma için assert_causal."""
from grafik_analiz.research import assert_causal
from grafik_analiz.strategies.kirilim import specs

for spec in specs():
    assert_causal(spec)
    assert_causal(spec, fractions=(0.3, 0.5, 0.71, 0.9, 0.999))
    print("assert_causal geçti:", spec.name, spec.params)
