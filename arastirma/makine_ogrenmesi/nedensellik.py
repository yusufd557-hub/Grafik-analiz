"""Dondurulan her yapılandırma için ileri bakış denetimi (assert_causal).

Getiri hesaplanmaz, deftere yazılmaz. Kullanım: python nedensellik.py [spec adı ...]
(ad verilmezse specs() içindeki hepsi). Varsayılan kesim oranlarına ek olarak
dev_train içine düşen erken bir kesim (0,3) de denenir.
"""
import sys
import time

from grafik_analiz.research import assert_causal
from grafik_analiz.strategies.makine_ogrenmesi import specs

secili = set(sys.argv[1:])
for spec in specs():
    if secili and spec.name not in secili:
        continue
    t0 = time.time()
    assert_causal(spec)
    assert_causal(spec, fractions=(0.3,))
    print(f"assert_causal geçti: {spec.name} ({time.time() - t0:.0f}s)", flush=True)
