"""Dondurulmuş yapılandırmaların ileri bakış denetimi (getiri hesaplanmaz)."""
from grafik_analiz.research import assert_causal
from grafik_analiz.strategies.rotasyon import specs

for spec in specs():
    assert spec.family == "rotasyon"
    assert_causal(spec)
    print("assert_causal geçti:", spec.name)
