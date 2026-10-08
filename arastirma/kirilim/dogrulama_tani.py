"""Dondurma ve tek değerlendirmeden SONRA tanı (seçimi değiştirmez): bacak, yıl, yön,
maruziyet, en iyi işlem çıkınca getiri, al-tut ile korelasyon. Ek DSR duyarlılığı."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import PERIODS, StrategySpec, daily_returns, deflated_sharpe, run, summarize
from grafik_analiz.research import ledger
from grafik_analiz.research.metrics import window
from grafik_analiz.strategies.kirilim import specs

HERE = Path(__file__).resolve().parent
start, end = PERIODS["dev_valid"]
out = {}
daily = {}

def hep_uzun(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}

for spec in specs():
    r = run(spec, "dev", 1.0)
    v = window(r.returns, start, end)
    tv = r.trades[(r.trades["entry_time"] >= start) & (r.trades["entry_time"] < end)]
    s = summarize(r.returns, r.trades, r.exposure, r.costs, r.funding, start, end)
    d = {"ozet": {k: s.get(k) for k in ("total_return", "sharpe", "max_drawdown", "trades", "exposure", "win_rate", "profit_factor", "best_trade", "total_without_best", "total_costs", "total_funding", "avg_bars")}}
    d["yillar"] = {}
    for y, ry in v.groupby(v.index.year):
        ty = tv[tv["entry_time"].dt.year == y]
        sy = summarize(ry, ty)
        d["yillar"][int(y)] = {"getiri": sy.get("total_return"), "sharpe": sy.get("sharpe"), "islem": sy.get("trades")}
    d["bacaklar"] = {}
    for leg, lr in r.legs.items():
        sl = summarize(lr.net, lr.trades, None, None, None, start, end)
        d["bacaklar"][f"{leg[0]}:{leg[1]}"] = {"getiri": sl.get("total_return"), "sharpe": sl.get("sharpe"), "mdd": sl.get("max_drawdown"), "islem": sl.get("trades")}
    d["yon"] = {int(k): {"n": int(len(g)), "toplam_net": float(g["net_return"].sum())} for k, g in tv.groupby("direction")}
    bh = run(StrategySpec("bh", "kirilim_kiyas", spec.interval, spec.legs, hep_uzun, {}), "dev", 1.0)
    db = daily_returns(window(bh.returns, start, end))
    ds = daily_returns(v)
    daily[spec.name] = ds
    d["al_tut_korelasyon_gunluk"] = float(ds.corr(db))
    d["beta_al_tuta"] = float(np.cov(ds, db)[0, 1] / np.var(db, ddof=1))
    out[spec.name] = d

names = list(daily)
out["korelasyon"] = {f"{a}~{b}": float(daily[a].corr(daily[b])) for i, a in enumerate(names) for b in names[i + 1:]}

# Ek DSR duyarlılığı: deneme varyansı yalnız 4h kanal denemelerinden (resmi DSR değil).
t = ledger.trials("kirilim")
tr = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
sel = tr[tr["parametreler"].apply(lambda p: p.get("interval") == "4h" and p.get("yontem") == "kanal")]
sh_all = np.array([o.get("sharpe") for o in tr["olcu"]], dtype=float)
sh_k = np.array([o.get("sharpe") for o in sel["olcu"]], dtype=float)
res = json.loads((HERE / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
out["dsr_duyarlilik"] = {}
for name, d in res.items():
    g = d["dsr_girdi"]
    out["dsr_duyarlilik"][name] = {
        "resmi_dsr": d["dsr"],
        "yalniz_4h_kanal_varyansi_ile": deflated_sharpe(g["sr"], g["n_days"], len(tr), float(np.nanvar(sh_k, ddof=1)), g["skew"], g["kurt"]),
        "4h_kanal_deneme_sayisi_ve_varyansi_ile": deflated_sharpe(g["sr"], g["n_days"], len(sel), float(np.nanvar(sh_k, ddof=1)), g["skew"], g["kurt"]),
        "n_4h_kanal": int(len(sel)), "var_4h_kanal": float(np.nanvar(sh_k, ddof=1)), "var_tum": float(np.nanvar(sh_all, ddof=1)),
    }
(HERE / "dogrulama_tani.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
