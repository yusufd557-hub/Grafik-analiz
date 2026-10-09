"""Dondurulan yapılandırmaların dev_valid'den ÖNCE kontrolü (deftere yazılmaz):
1) spec parametreleri defterdeki arama satırıyla aynı mı,
2) assert_causal (varsayılan + ek kesimler),
3) dev_train günlük getiri korelasyonları (veri DEV_TRAIN_END'de kesilir)."""
import json

import pandas as pd

from grafik_analiz.research.backtest import backtest_leg, combine
from grafik_analiz.research.evaluate import assert_causal, load_data
from grafik_analiz.research.ledger import trials
from grafik_analiz.research.metrics import daily_returns
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies import t2_limit_gun_ici as lg

assert PROTOCOL_VERSION == "2"
led = trials("t2_limit_gun_ici")
daily = {}
for spec in lg.specs():
    p = {"interval": spec.interval, "legs": [list(l) for l in spec.legs], **spec.params}
    key = json.dumps(json.loads(json.dumps(p)), sort_keys=True)
    rows = led[led["strateji"] == spec.name]
    same = any(json.dumps(r, sort_keys=True) == key for r in rows["parametreler"])
    print(spec.name, "defterle_ayni:", same, flush=True)
    assert same
    assert_causal(spec)
    assert_causal(spec, fractions=(0.3, 0.5, 0.7, 0.9, 0.99))
    print("  assert_causal: gecti", flush=True)
    data, funding = load_data(spec, "dev")
    data = {k: v[v.index < DEV_TRAIN_END] for k, v in data.items()}
    funding = {k: v[v.index < DEV_TRAIN_END] for k, v in funding.items()}
    sig = spec.signal_fn(data, funding, **spec.params)
    legs = {leg: backtest_leg(data[leg], sig[leg], market=leg[0], symbol=leg[1], funding=funding.get(leg[1])) for leg in spec.legs}
    daily[spec.name.replace("t2_limit_gun_ici_", "")] = daily_returns(combine(legs))
df = pd.DataFrame(daily).dropna()
print("dev_train gunluk getiri korelasyonu:")
print(df.corr().round(2).to_string())
