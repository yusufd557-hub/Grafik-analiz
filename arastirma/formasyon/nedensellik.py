"""Dondurulan yapılandırmalar için assert_causal (varsayılan kesimler + ek kesimler). Getiri hesaplamaz.

Modül içi önbellek her denetimden önce boşaltılır (önbellek sonucu etkilemesin diye).
"""
import time

from grafik_analiz.research import assert_causal
from grafik_analiz.strategies import formasyon as F

for spec in F.specs():
    t0 = time.time()
    for fr in ((0.55, 0.8, 0.97), (0.3, 0.5, 0.71, 0.9, 0.999)):
        F._CACHE.clear()
        assert_causal(spec, fractions=fr)
    print("geçti:", spec.name, f"{time.time() - t0:.1f} sn", flush=True)
