"""Hız ve işlerlik denemesi (deftere yazmaz: record=False). Yalnız dev_train."""
import time
from grafik_analiz.research.evaluate import evaluate
from grafik_analiz.strategies.t2_lead_lag import make_spec

for name, iv, p in [
    ("hiz_yetis", "5m", dict(tur="yetis", islem=["ETHUSDT"], k=1, esik=4.0, tut=1)),
    ("hiz_yetis_lim", "5m", dict(tur="yetis", islem=["ETHUSDT"], k=1, esik=4.0, tut=1, limit_bps=2, limit_mod="tum", limit_bar=3)),
    ("hiz_sv", "15m", dict(tur="spot_vadeli", islem=["BTCUSDT"], kaynak="kendi", k=1, esik=4.0, tut=12)),
    ("hiz_prim", "1h", dict(tur="prim", islem=["BTCUSDT"], win=168, esik=2.0, tut=8)),
]:
    t = time.time()
    spec = make_spec(name, iv, **p)
    r = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0,), record=False)
    m = r["dev_train"][1.0]
    print(name, spec.legs, {k: round(m[k], 4) if isinstance(m.get(k), float) else m.get(k) for k in ("total_return", "sharpe", "trades", "alfa", "beta", "total_costs", "exposure")}, f"{time.time()-t:.1f}s")
