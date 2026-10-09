"""Dondurulan 5 yapılandırmanın TEK SEFERLİK dev_train + dev_valid değerlendirmesi (1× ve 2×),
candidate_check, Deflated Sharpe ve al-tut kıyası. Sonuçlar dogrulama_sonuc.json'a yazılır.
Bu betik bir kez çalıştırılır; sonuçlara bakarak hiçbir parametre değiştirilmez."""
import json
import math

import numpy as np
import pandas as pd

from grafik_analiz.research.backtest import backtest_leg, combine
from grafik_analiz.research.data import load, load_funding
from grafik_analiz.research.evaluate import backtest, candidate_check, compute_signals, evaluate, load_data
from grafik_analiz.research.ledger import trials
from grafik_analiz.research.metrics import daily_returns, deflated_sharpe, summarize, window
from grafik_analiz.research.protocol import PERIODS, PROTOCOL_VERSION
from grafik_analiz.strategies import t2_limit_gun_ici as lg

assert PROTOCOL_VERSION == "2"

KEYS = ("total_return", "cagr", "sharpe", "max_drawdown", "trades", "win_rate", "exposure", "alfa", "beta", "alfa_t",
        "p_value", "skew", "kurtosis", "days", "total_costs", "total_funding", "total_without_best", "avg_bars")

led0 = trials("t2_limit_gun_ici")
out = {"yapilandirmalar": []}
for spec in lg.specs():
    onceki = led0[(led0["strateji"] == spec.name) & (led0["pencere"] == "dev_train") & (led0["maliyet_kat"] == 1.0)]
    res = evaluate(spec)  # dev_train + dev_valid, 1× ve 2× — deftere yazılır (tek bakış)
    cc = candidate_check(res)
    data, funding = load_data(spec, "dev")
    sig = compute_signals(spec, data, funding)
    rr = backtest(spec, data, funding, sig, 1.0)
    s, e = PERIODS["dev_valid"]
    dv = daily_returns(window(rr.returns, s, e))
    legs = {}
    for leg, lr in rr.legs.items():
        n = window(lr.net, s, e)
        legs[leg[1]] = float((1 + n).prod() - 1)
    yil = (1 + window(rr.returns, s, e)).groupby(window(rr.returns, s, e).index.year).prod() - 1
    row = {
        "ad": spec.name,
        "aralik": spec.interval,
        "parametreler": spec.params,
        "onceki_dev_train_getiri": float(onceki["olcu"].iloc[0]["total_return"]) if len(onceki) else None,
        "sonuclar": {w: {str(k): {kk: res[w][k].get(kk) for kk in KEYS} for k in res[w]} for w in res},
        "candidate_check": cc,
        "dev_valid_gun_sayisi": int(len(dv)),
        "dev_valid_bacak_getirisi": legs,
        "dev_valid_yillik": {str(k): float(v) for k, v in yil.items()},
    }
    out["yapilandirmalar"].append(row)
    v1, v2, t1 = res["dev_valid"][1.0], res["dev_valid"][2.0], res["dev_train"][1.0]
    print(f"{spec.name}\n  dev_train 1x {t1['total_return']*100:+.2f}% (arama satiri {row['onceki_dev_train_getiri']*100:+.2f}%) sh {t1['sharpe']:.2f} a {t1['alfa']*100:+.1f}% b {t1['beta']:+.3f}"
          f"\n  dev_valid 1x {v1['total_return']*100:+.2f}% 2x {v2['total_return']*100:+.2f}% sh {v1['sharpe']:.2f}/{v2['sharpe']:.2f} dd {v1['max_drawdown']*100:.2f}% n {v1['trades']} a {v1['alfa']*100:+.2f}% b {v1['beta']:+.3f} t {v1['alfa_t']:+.2f}"
          f"\n  aday: {cc['aday']} {cc}\n  bacak {legs} yil {row['dev_valid_yillik']}", flush=True)

# Deflated Sharpe: deneme = defterde pencere==dev_train ve maliyet_kat==1.0 satırları (son evaluate dahil)
led = trials("t2_limit_gun_ici")
tr = led[(led["pencere"] == "dev_train") & (led["maliyet_kat"] == 1.0)]
sh = np.array([r.get("sharpe") for r in tr["olcu"]], dtype=float)
sh = sh[np.isfinite(sh)]
var = float(np.var(sh, ddof=1))
out["dsr"] = {"deneme": int(len(tr)), "sharpe_varyans": var, "sharpe_std": math.sqrt(var)}
for row in out["yapilandirmalar"]:
    v = row["sonuclar"]["dev_valid"]["1.0"]
    row["dsr"] = deflated_sharpe(v["sharpe"], row["dev_valid_gun_sayisi"], len(tr), var, v["skew"], v["kurtosis"])
    print(f"DSR {row['ad']}: {row['dsr']:.4f} (N={len(tr)}, var={var:.3f}, sh={v['sharpe']:.2f}, skew={v['skew']:.2f}, kurt={v['kurtosis']:.1f})", flush=True)

# Al-tut kıyası (vadeli BTC/ETH/SOL eşit ağırlık, 1h, fonlama dahil, giriş/çıkış maliyeti dahil; deftere yazılmaz)
bh_legs = {}
for c in lg.COINS:
    df = load(c, "1h", "futures", scope="dev")
    fu = load_funding(c, scope="dev")
    bh_legs[("futures", c)] = backtest_leg(df, pd.Series(1.0, index=df.index), market="futures", symbol=c, funding=fu)
bh = combine(bh_legs)
out["al_tut"] = {}
for w in ("dev_train", "dev_valid"):
    s, e = PERIODS[w]
    m = summarize(bh, start=s, end=e)
    out["al_tut"][w] = {k: m.get(k) for k in ("total_return", "sharpe", "max_drawdown", "start", "end")}
    tek = {}
    for (mk, c), lr in bh_legs.items():
        tek[c] = summarize(lr.net, start=s, end=e).get("total_return")
    out["al_tut"][w]["coin"] = tek
    print(f"al-tut {w}: {m['total_return']*100:+.1f}% sh {m['sharpe']:.2f} dd {m['max_drawdown']*100:.1f}% coin {tek}", flush=True)

with open("dogrulama_sonuc.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
