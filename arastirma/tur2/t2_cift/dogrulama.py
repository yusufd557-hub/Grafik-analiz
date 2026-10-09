"""Tek seferlik iç doğrulama (dev_valid) değerlendirmesi — dondurulan 3 yapılandırma.

Her spec için yalnız bir kez `evaluate(spec)` (dev_train + dev_valid, 1× ve 2×; deftere yazılır),
`candidate_check`, Deflated Sharpe (deneme = defterdeki dev_train 1× satırları) ve al-tut kıyası.
Sonuç `dogrulama_sonuc.json`. Bu betik bir kez çalıştırılır; sonrasında parametre değişmez.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import benchmark_daily, candidate_check, evaluate, run
from grafik_analiz.research.ledger import _clean, trials
from grafik_analiz.research.metrics import daily_returns, deflated_sharpe, window
from grafik_analiz.strategies.t2_cift import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"
HERE = Path(__file__).resolve().parent
OUT = HERE / "dogrulama_sonuc.json"
assert not OUT.exists(), "dogrulama zaten çalıştırılmış — tekrar çalıştırılmaz"

KEYS = ("total_return", "cagr", "sharpe", "sortino", "volatility", "max_drawdown", "trades", "win_rate",
        "profit_factor", "avg_trade", "best_trade", "total_without_best", "exposure", "total_costs",
        "total_funding", "p_value", "skew", "kurtosis", "days", "start", "end", "alfa", "beta", "alfa_t")

results = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sonuclar": {}}
for spec in specs():
    res = evaluate(spec)  # tek bakış
    chk = candidate_check(res)
    m = {w: {str(c): {k: v.get(k) for k in KEYS} for c, v in res[w].items()} for w in res}
    results["sonuclar"][spec.name] = {"metrics": m, "candidate_check": chk}
    OUT.write_text(json.dumps(_clean(results), ensure_ascii=False, indent=1), encoding="utf-8")
    v1 = res["dev_valid"][1.0]
    print(spec.name, "| valid 1x", round(v1["total_return"], 4), "2x", round(res["dev_valid"][2.0]["total_return"], 4),
          "Sharpe", round(v1["sharpe"], 3), "işlem", v1["trades"], "alfa", round(v1["alfa"], 4), "aday", chk["aday"], flush=True)

# Deflated Sharpe: deneme sayısı = defterdeki dev_train 1× satırları (dondurulanların tekrarı dahil)
t = trials(FAMILY)
t = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
sr = t["olcu"].apply(lambda o: o.get("sharpe")).astype(float).dropna()
n_rows = int(len(t))
n_unique = int(t["parametreler"].apply(lambda p: json.dumps(p, sort_keys=True)).nunique())
var_sr = float(sr.var(ddof=1))
results["dsr_girdi"] = {"deneme_satir": n_rows, "deneme_benzersiz": n_unique, "sharpe_varyans": var_sr}
for name, r in results["sonuclar"].items():
    v = r["metrics"]["dev_valid"]["1.0"]
    r["deflated_sharpe"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_rows, var_sr, v["skew"], v["kurtosis"])
    r["deflated_sharpe_benzersiz"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_unique, var_sr, v["skew"], v["kurtosis"])

# Al-tut kıyası: BTC/ETH/SOL eşit ağırlıklı vadeli al-tut (alfa kıyası) ve tek tek coinler
spec0 = specs()[0]
bench = benchmark_daily(spec0, "dev")
bh = {}
for w in ("dev_train", "dev_valid"):
    s, e = protocol.PERIODS[w]
    d = window(bench, s, e).dropna()
    eq = (1 + d).cumprod()
    bh[w] = {"getiri": float(eq.iloc[-1] - 1), "sharpe": float(d.mean() / d.std(ddof=1) * math.sqrt(365)),
             "max_dusus": float((eq / eq.cummax() - 1).min())}
results["al_tut_port3_vadeli"] = bh

# dev_valid yıllık döküm ve fonlama payı (betimleyici, sonradan; parametre değişmez)
for spec in specs():
    r = run(spec, "dev", 1.0)
    rv = window(r.returns, *protocol.PERIODS["dev_valid"])
    yearly = ((1 + rv).groupby(rv.index.year).prod() - 1).round(4).to_dict()
    fv = window(r.funding, *protocol.PERIODS["dev_valid"])
    cv = window(r.costs, *protocol.PERIODS["dev_valid"])
    tr = r.trades
    tv = tr[(tr["entry_time"] >= protocol.DEV_TRAIN_END)]
    results["sonuclar"][spec.name]["dev_valid_dokum"] = {
        "yillik": {str(k): v for k, v in yearly.items()},
        "fonlama_toplam_odenen": float(fv.sum()),
        "maliyet_toplam": float(cv.sum()),
        "bacak_islem": tv.groupby("leg").size().to_dict(),
    }
OUT.write_text(json.dumps(_clean(results), ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(_clean({k: v for k, v in results.items() if k != "sonuclar"}), ensure_ascii=False, indent=1))
for name, r in results["sonuclar"].items():
    print(name, "DSR", r["deflated_sharpe"], "DSR(benzersiz)", r["deflated_sharpe_benzersiz"], r["dev_valid_dokum"])
