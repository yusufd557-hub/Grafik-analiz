"""Dondurulan yapılandırmaların TEK SEFERLİK değerlendirmesi (dev_train + dev_valid, 1× ve 2×).

Her yapılandırma bir kez değerlendirilir; sonuç dondurulmus/<ad>.json dosyasına yazılır ve
dosya varsa betik o yapılandırmayı tekrar değerlendirmez. Kullanım:
python dogrulama.py [spec adı ...]  (ad verilmezse specs() içindeki hepsi)

Ek tanılar (deftere yazılmaz, aynı süreçteki önbellekten): dev_valid'de yıl ve bacak bazında
getiri, günlük getiri serisi (korelasyon için) ve günlük gözlem sayısı (Deflated Sharpe için).
"""
import json
import math
import sys
import time
from pathlib import Path

import pandas as pd

from grafik_analiz.research import PERIODS, candidate_check, daily_returns, evaluate, run
from grafik_analiz.research.metrics import window
from grafik_analiz.strategies.makine_ogrenmesi import specs

HERE = Path(__file__).resolve().parent
OUT = HERE / "dondurulmus"
OUT.mkdir(exist_ok=True)


def temiz(x):
    if isinstance(x, dict):
        return {str(k): temiz(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [temiz(v) for v in x]
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    return x


secili = set(sys.argv[1:])
for spec in specs():
    if secili and spec.name not in secili:
        continue
    path = OUT / f"{spec.name}.json"
    if path.exists():
        print("zaten değerlendirildi, atlanıyor:", spec.name, flush=True)
        continue
    t0 = time.time()
    res = evaluate(spec)  # dev_train + dev_valid, 1× ve 2×; deftere yazılır
    cc = candidate_check(res)
    start, end = PERIODS["dev_valid"]
    ek = {}
    for mult in (1.0, 2.0):
        r = run(spec, "dev", mult)  # aynı sinyaller (süreç içi önbellek), deftere yazılmaz
        rv = window(r.returns, start, end)
        d = daily_returns(rv)
        yil = {str(y): float((1 + g).prod() - 1) for y, g in rv.groupby(rv.index.year)}
        bacak = {}
        for leg, lr in r.legs.items():
            if spec.leg_weights()[leg] == 0:
                continue
            n = window(lr.net, start, end)
            bacak[f"{leg[0]}:{leg[1]}"] = float((1 + n).prod() - 1)
        ek[str(mult)] = {"yil": yil, "bacak": bacak, "n_gun": int(len(d))}
        if mult == 1.0:
            d.index = d.index.strftime("%Y-%m-%d")
            ek["gunluk_1x"] = {k: float(v) for k, v in d.items()}
    kayit = {
        "ad": spec.name, "interval": spec.interval, "legs": [list(l) for l in spec.legs], "params": spec.params,
        "metrics": {w: {str(m): v for m, v in dd.items()} for w, dd in res.items()},
        "candidate_check": cc, "ek": ek, "sure_s": round(time.time() - t0, 1),
    }
    path.write_text(json.dumps(temiz(kayit), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("==", spec.name, flush=True)
    for w in ("dev_train", "dev_valid"):
        for m in (1.0, 2.0):
            x = res[w][m]
            print(f"  {w} {m}x: getiri={x['total_return']:+.4f} sharpe={x['sharpe']:.3f} mdd={x['max_drawdown']:.3f} "
                  f"islem={x.get('trades')} pozda={x.get('exposure', float('nan')):.3f} maliyet={x.get('total_costs', float('nan')):.3f} "
                  f"p={x['p_value']:.3f}", flush=True)
    print("  candidate_check:", cc, flush=True)
    print("  dev_valid yıl (1x):", {k: round(v, 4) for k, v in ek["1.0"]["yil"].items()},
          "bacak (1x):", {k: round(v, 4) for k, v in ek["1.0"]["bacak"].items()}, flush=True)
