"""Dondurma sonrası tanılar (seçimi değiştirmez). dondurulmus_sonuclar.json'daki tek değerlendirmenin
aynı spec'leriyle run() → dev_valid parçalara ayrılır: yıl, bacak, yön, maliyet/fonlama, korelasyon/beta.
Ayrıca DSR duyarlılığı (bilgi amaçlı, resmi değil)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import PERIODS, StrategySpec, daily_returns, deflated_sharpe, run, summarize
from grafik_analiz.research.ledger import trials
from grafik_analiz.strategies.formasyon import specs

HERE = Path(__file__).resolve().parent
vs, ve = PERIODS["dev_valid"]
out = {}
daily = {}


def hep_uzun(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}


for spec in specs():
    res = run(spec, "dev", 1.0)
    r = res.returns[(res.returns.index >= vs) & (res.returns.index < ve)]
    tr = res.trades[(res.trades["entry_time"] >= vs) & (res.trades["entry_time"] < ve)]
    daily[spec.name] = daily_returns(r)
    o = {}
    for y, ry in r.groupby(r.index.year):
        ty = tr[tr["entry_time"].dt.year == y]
        s = summarize(ry, ty)
        o[f"yil_{y}"] = {"getiri": s["total_return"], "sharpe": s["sharpe"], "islem": s.get("trades")}
    for leg, lr in res.legs.items():
        nl = lr.net[(lr.net.index >= vs) & (lr.net.index < ve)]
        tl = lr.trades[(lr.trades["entry_time"] >= vs) & (lr.trades["entry_time"] < ve)]
        s = summarize(nl, tl)
        o[f"bacak_{leg[1]}"] = {"getiri": s["total_return"], "sharpe": s["sharpe"], "islem": s.get("trades")}
    for d_, td in tr.groupby("direction"):
        o[f"yon_{int(d_)}"] = {"islem": int(len(td)), "toplam_net": float(td["net_return"].sum()), "kazanma": float((td["net_return"] > 0).mean())}
    s = summarize(r, tr, res.exposure, res.costs, res.funding, vs, ve)
    o["genel"] = {k: s.get(k) for k in ("total_return", "sharpe", "max_drawdown", "trades", "win_rate", "profit_factor", "best_trade",
                                         "total_without_best", "exposure", "total_costs", "total_funding", "avg_bars", "p_value")}
    out[spec.name] = o

bh = run(StrategySpec("al_tut", "formasyon_kiyas", "4h", tuple(("futures", c) for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT")), hep_uzun, {}), "dev", 1.0)
bhd = daily_returns(bh.returns[(bh.returns.index >= vs) & (bh.returns.index < ve)])
df = pd.DataFrame(daily).join(bhd.rename("AL_TUT"), how="inner")
corr = df.corr().round(2)
betas = {k: float(df[k].cov(df["AL_TUT"]) / df["AL_TUT"].var()) for k in daily}
for name in out:
    out[name]["al_tut_korelasyon"] = float(corr.loc[name, "AL_TUT"])
    out[name]["al_tut_beta"] = betas[name]
bh_years = {}
for y, ry in bh.returns[(bh.returns.index >= vs) & (bh.returns.index < ve)].groupby(lambda i: i.year):
    s = summarize(ry)
    bh_years[int(y)] = {"getiri": s["total_return"], "sharpe": s["sharpe"]}

# DSR duyarlılığı (resmi değil): deneme varyansı yalnız 4h grafik denemelerinden
t = trials("formasyon")
t = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
iv = t["parametreler"].apply(lambda p: p.get("interval"))
yt = t["parametreler"].apply(lambda p: p.get("yontem"))
sub = t[(iv == "4h") & (yt == "grafik")]
sh = pd.to_numeric(sub["olcu"].apply(lambda o: o.get("sharpe")), errors="coerce").to_numpy(dtype=float)
var4h = float(np.nanvar(sh, ddof=1))
res_json = json.loads((HERE / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
sens = {}
for name, r in res_json.items():
    v = r["sonuc"]["dev_valid"]["1.0"]
    sens[name] = {"dsr_4h_grafik_varyans_tum_deneme": deflated_sharpe(v["sharpe"], 547, len(t), var4h, v["skew"], v["kurtosis"]),
                  "dsr_4h_grafik_varyans_ve_sayi": deflated_sharpe(v["sharpe"], 547, len(sub), var4h, v["skew"], v["kurtosis"])}

result = {"stratejiler": out, "korelasyon": corr.to_dict(), "al_tut_yillar": bh_years,
          "dsr_duyarlilik": {"4h_grafik_deneme": len(sub), "4h_grafik_varyans": var4h, "degerler": sens}}
(HERE / "dogrulama_tani.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
pd.set_option("display.width", 220)
for name, o in out.items():
    print(f"\n== {name}")
    for k, v in o.items():
        print(f"  {k}: {v}")
print("\nkorelasyon (dev_valid günlük):\n", corr)
print("al-tut yılları:", bh_years)
print("DSR duyarlılık: 4h grafik deneme", len(sub), "varyans", round(var4h, 4), sens)
