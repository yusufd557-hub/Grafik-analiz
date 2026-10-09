"""Tek seferlik iç doğrulama (dev_valid) değerlendirmesi — dondurulan 5 yapılandırma.

Her spec için yalnız bir kez `evaluate(spec)` (dev_train + dev_valid, 1× ve 2×; deftere yazılır),
`candidate_check`, Deflated Sharpe (deneme = defterdeki dev_train 1× satırları), al-tut kıyası ve
betimleyici döküm. Sonuç `dogrulama_sonuc.json`. Bu betik bir kez çalıştırılır; sonrasında
parametre değişmez.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import backtest, benchmark_daily, candidate_check, compute_signals, evaluate, load_data
from grafik_analiz.research.ledger import _clean, ledger_path
from grafik_analiz.research.metrics import daily_returns, deflated_sharpe, window
from grafik_analiz.strategies.t2_lead_lag import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"
HERE = Path(__file__).resolve().parent
OUT = HERE / "dogrulama_sonuc.json"
assert not OUT.exists(), "dogrulama zaten çalıştırılmış — tekrar çalıştırılmaz"

KEYS = ("total_return", "cagr", "sharpe", "sortino", "volatility", "max_drawdown", "trades", "win_rate",
        "profit_factor", "avg_trade", "best_trade", "total_without_best", "exposure", "total_costs",
        "total_funding", "p_value", "skew", "kurtosis", "days", "start", "end", "alfa", "beta", "alfa_t", "avg_bars")

results = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sonuclar": {}}
for spec in specs():
    res = evaluate(spec)  # tek bakış
    chk = candidate_check(res)
    m = {w: {str(c): {k: v.get(k) for k in KEYS} for c, v in res[w].items()} for w in res}
    results["sonuclar"][spec.name] = {"metrics": m, "candidate_check": chk}
    OUT.write_text(json.dumps(_clean(results), ensure_ascii=False, indent=1), encoding="utf-8")
    v1, v2, t1 = res["dev_valid"][1.0], res["dev_valid"][2.0], res["dev_train"][1.0]
    print(f"{spec.name} | train {t1['total_return']:+.4f} alfa {t1['alfa']:+.4f} | valid 1x {v1['total_return']:+.4f} "
          f"2x {v2['total_return']:+.4f} Sharpe {v1['sharpe']:+.3f} dd {v1['max_drawdown']:+.4f} işlem {v1['trades']} "
          f"alfa {v1['alfa']:+.4f} beta {v1['beta']:+.3f} t {v1['alfa_t']:+.2f} | aday {chk['aday']}", flush=True)

# Deflated Sharpe: deneme = defterdeki dev_train 1× satırları (dondurulanların tekrarı dahil)
rows = [json.loads(l) for l in ledger_path(FAMILY).open(encoding="utf-8")]
tr = [r for r in rows if r["pencere"] == "dev_train" and r["maliyet_kat"] == 1.0]
sr = np.array([r["olcu"].get("sharpe") for r in tr if r["olcu"].get("sharpe") is not None], dtype=float)
n_rows = len(tr)
n_unique = len({json.dumps(r["parametreler"], sort_keys=True) for r in tr})
var_sr = float(np.var(sr, ddof=1))
results["dsr_girdi"] = {"deneme_satir": n_rows, "deneme_benzersiz": n_unique, "sharpe_varyans": var_sr,
                        "sharpe_ort": float(np.mean(sr)), "sharpe_max": float(np.max(sr))}
for name, r in results["sonuclar"].items():
    v = r["metrics"]["dev_valid"]["1.0"]
    t = r["metrics"]["dev_train"]["1.0"]
    r["deflated_sharpe"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_rows, var_sr, v["skew"], v["kurtosis"])
    r["deflated_sharpe_benzersiz"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_unique, var_sr, v["skew"], v["kurtosis"])
    r["deflated_sharpe_egitim"] = deflated_sharpe(t["sharpe"], int(t["days"]), n_rows, var_sr, t["skew"], t["kurtosis"])
    print(f"DSR {name}: valid {r['deflated_sharpe']:.4f} (benzersiz {r['deflated_sharpe_benzersiz']:.4f}) eğitim {r['deflated_sharpe_egitim']:.4f}")
print("DSR girdi:", results["dsr_girdi"])

# Al-tut kıyası: BTC/ETH/SOL eşit ağırlıklı vadeli al-tut (alfa kıyası)
spec0 = specs()[0]
bench = benchmark_daily(spec0, "dev")
bh = {}
for w in ("dev_train", "dev_valid"):
    s, e = protocol.PERIODS[w]
    d = window(bench, s, e).dropna()
    eq = (1 + d).cumprod()
    bh[w] = {"getiri": float(eq.iloc[-1] - 1), "sharpe": float(d.mean() / d.std(ddof=1) * math.sqrt(365)),
             "max_dusus": float((eq / eq.cummax() - 1).min()), "baslangic": str(d.index[0].date()), "bitis": str(d.index[-1].date())}
results["al_tut_vadeli_port3"] = bh
print("Al-tut (vadeli BTC/ETH/SOL eşit ağırlık):", bh)

# Betimleyici dev_valid dökümü (değerlendirmeden sonra; parametre değişmez)
s, e = protocol.PERIODS["dev_valid"]
daily_v = {}
for spec in specs():
    data, funding = load_data(spec, "dev")
    r = backtest(spec, data, funding, compute_signals(spec, data, funding), 1.0)
    rv = window(r.returns, s, e)
    dv = daily_returns(rv)
    daily_v[spec.name] = dv
    tv = r.trades[r.trades["entry_time"] >= s]
    yon = {str(int(k)): {"islem": int(len(g)), "toplam_net": float(g.net_return.sum())} for k, g in tv.groupby("direction")}
    bacak = {k: {"islem": int(len(g)), "toplam_net": float(g.net_return.sum())} for k, g in tv.groupby("leg")}
    srt = tv.sort_values("net_return", ascending=False)
    tot = float((1 + rv).prod() - 1)
    wo = {n: float(np.expm1(np.log1p(tot) - np.log1p(srt["net_return"].head(n)).sum())) for n in (1, 5, 10)}
    ay = (1 + dv).groupby(dv.index.strftime("%Y-%m")).prod() - 1
    en_iyi = [{"giris": str(x.entry_time), "bacak": x.leg, "yon": int(x.direction), "net": float(x.net_return)} for x in srt.head(5).itertuples()]
    en_kotu = [{"giris": str(x.entry_time), "bacak": x.leg, "yon": int(x.direction), "net": float(x.net_return)} for x in srt.tail(5).itertuples()]
    results["sonuclar"][spec.name]["dokum_dev_valid"] = {
        "yon": yon, "bacak": bacak, "en_iyi_n_cikinca": wo, "aylik": {k: float(v) for k, v in ay.items()},
        "en_iyi_5": en_iyi, "en_kotu_5": en_kotu,
    }
    print(f"{spec.name}: yön {yon} | en iyi 1/5/10 çıkınca {wo}")
corr = pd.DataFrame(daily_v).fillna(0.0).corr()
results["korelasyon_dev_valid"] = {a: {b: float(corr.loc[a, b]) for b in corr.columns} for a in corr.index}
print(corr.round(2).to_string())
OUT.write_text(json.dumps(_clean(results), ensure_ascii=False, indent=1), encoding="utf-8")
print("yazıldı", OUT)
