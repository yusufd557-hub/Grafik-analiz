"""dev_valid SONRASI betimleyici tanı (hiçbir parametreyi değiştirmez; yeni yapılandırma ölçmez).

Dondurulan yapılandırmaların kendi olaylarında: dönem bazında AUC, kabul / red edilen olayların
ortalama net getirisi (meta modelin örneklem dışı katkısı) ve yıl / coin / yön kırılımı.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402
from grafik_analiz.research.evaluate import benchmark_daily, load_data, run  # noqa: E402
from grafik_analiz.research.metrics import alpha_beta, daily_returns, sharpe  # noqa: E402
from grafik_analiz.research.protocol import DEV_END, DEV_TRAIN_END  # noqa: E402
from grafik_analiz.strategies import t2_meta as tm  # noqa: E402

for spec in tm.specs():
    data, funding = load_data(spec, "dev")
    q0 = {**tm.DEFAULTS, **spec.params}
    print(f"== {spec.name}")
    for label, a, b in (("egitim", 0, DEV_TRAIN_END.value), ("dogrulama", DEV_TRAIN_END.value, DEV_END.value)):
        nets, prs, accs = [], [], []
        for q in tm.expand_ensemble(q0):
            ev = tm.predictions(data, funding, q)
            ev = ev[(ev["_ts"].to_numpy() >= a) & (ev["_ts"].to_numpy() < b) & (ev["_known"].to_numpy() < b)]
            acc, _ = tm.decisions(ev, q)
            nets.append(ev["_net"].to_numpy(float)); prs.append(ev["_p"].to_numpy(float)); accs.append(acc)
        net, pr, acc = map(np.concatenate, (nets, prs, accs))
        m = np.isfinite(pr)
        y = (net > 0).astype(int)
        print(f"  {label}: olay {m.sum()} taban {y[m].mean():.3f} auc {ortak.auc(y[m], pr[m]):.3f} "
              f"hepsi_ort {net[m].mean():+.4f} kabul {int((acc & m).sum())} kabul_ort {net[acc & m].mean():+.4f} red_ort {net[m & ~acc].mean():+.4f}")
    res = run(spec)
    r = res.returns[res.returns.index >= DEV_TRAIN_END]
    bench = benchmark_daily(spec)
    rows = []
    for y_, g in r.groupby(r.index.year):
        d = daily_returns(g)
        ab = alpha_beta(d, bench)
        legs = {leg[1][:3]: float((1 + res.legs[leg].net[(res.legs[leg].net.index >= DEV_TRAIN_END) & (res.legs[leg].net.index.year == y_)]).prod() - 1) for leg in spec.legs}
        rows.append({"yil": y_, "getiri": float((1 + g).prod() - 1), "sharpe": sharpe(d), "alfa": ab["alfa"], "beta": ab["beta"], **legs})
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    tr = res.trades[res.trades["entry_time"] >= DEV_TRAIN_END]
    print("  islem", len(tr), "uzun", int((tr["direction"] > 0).sum()), "kisa", int((tr["direction"] < 0).sum()),
          "uzun_net_top", round(float(tr.loc[tr["direction"] > 0, "net_return"].sum()), 4),
          "kisa_net_top", round(float(tr.loc[tr["direction"] < 0, "net_return"].sum()), 4), flush=True)
