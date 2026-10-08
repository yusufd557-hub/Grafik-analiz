"""specs() yapılandırmalarının raporlanan sayıları yeniden ürettiğini denetler (run() + summarize;
deftere YAZILMAZ). Kullanım: python yeniden_uretim.py [spec adı ...]"""
import json
import sys
from pathlib import Path

from grafik_analiz.research import PERIODS, run, summarize
from grafik_analiz.strategies.makine_ogrenmesi import specs

HERE = Path(__file__).resolve().parent
secili = set(sys.argv[1:])
for spec in specs():
    if secili and spec.name not in secili:
        continue
    ref = json.loads((HERE / "dondurulmus" / f"{spec.name}.json").read_text(encoding="utf-8"))
    for mult in (1.0, 2.0):
        r = run(spec, "dev", mult)
        for w in ("dev_train", "dev_valid"):
            s, e = PERIODS[w]
            m = summarize(r.returns, r.trades, r.exposure, r.costs, r.funding, s, e)
            x = ref["metrics"][w][str(mult)]
            ok = all(abs(m[k] - x[k]) < 1e-9 for k in ("total_return", "sharpe", "max_drawdown")) and m["trades"] == x["trades"]
            print(f"{spec.name} {w} {mult}x getiri={m['total_return']:+.4f} sharpe={m['sharpe']:.3f} islem={m['trades']} -> {'AYNI' if ok else 'FARKLI'}", flush=True)
