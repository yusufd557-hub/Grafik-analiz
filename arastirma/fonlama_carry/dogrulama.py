"""Dondurulan yapılandırmaların TEK SEFERLİK değerlendirmesi: evaluate(spec) (dev_train + dev_valid, 1× ve 2×),
candidate_check, getiri ayrıştırması (fiyat / maliyet / fonlama). Sonuçlar dondurulmus_sonuclar.json'a yazılır.
Bu betik bir kez çalıştırılır; tekrar çalıştırılırsa deftere yinelenen satırlar ekler."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import PERIODS, candidate_check, evaluate, run
from grafik_analiz.strategies.fonlama_carry import specs

KLASOR = Path(__file__).resolve().parent
cikti = KLASOR / "dondurulmus_sonuclar.json"
if cikti.exists():
    raise SystemExit("dondurulmus_sonuclar.json zaten var: dondurulan yapılandırmalar yalnız bir kez değerlendirilir")


def temiz(v):
    if isinstance(v, dict):
        return {str(k): temiz(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [temiz(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


sonuc = {}
for spec in specs():
    res = evaluate(spec)
    chk = candidate_check(res)
    # Ayrıştırma (aynı deterministik backtest; deftere yazılmaz)
    rr = run(spec, "dev", 1.0)
    w = spec.leg_weights()
    ayr = {}
    for pen in ("dev_train", "dev_valid"):
        a, b = PERIODS[pen]
        m = lambda s: s[((s.index >= a) if a is not None else True) & (s.index < b)]
        fiyat = {f"{l[0]}:{l[1]}": float(w[l] * m(lr.gross).sum()) for l, lr in rr.legs.items()}
        r = m(rr.returns)
        t = rr.trades[(rr.trades["entry_time"] >= (a if a is not None else rr.trades["entry_time"].min())) & (rr.trades["entry_time"] < b)]
        ayr[pen] = {
            "fiyat_toplam": float(sum(fiyat.values())),
            "fiyat_bacak": fiyat,
            "maliyet_toplam": float(m(rr.costs).sum()),
            "fonlama_alinan": float(-m(rr.funding).sum()),
            "net_toplam_aritmetik": float(r.sum()),
            "donem_getirisi": {str(k): float(v) for k, v in ((1 + r).groupby(r.index.to_period("Q").astype(str)).prod() - 1).items()},
            "islem_ceyrek": {str(k): int(v) for k, v in t.groupby(pd.DatetimeIndex(t["entry_time"]).to_period("Q").astype(str)).size().items()},
            "maruziyet_ort": float(m(rr.exposure).mean()),
        }
    sonuc[spec.name] = {"params": spec.params, "interval": spec.interval, "legs": [list(l) for l in spec.legs],
                        "sonuclar": res, "candidate_check": chk, "ayristirma": ayr}
    v1 = res["dev_valid"][1.0]; v2 = res["dev_valid"][2.0]
    print(spec.name, "| valid 1x", round(v1["total_return"], 4), "S", round(v1["sharpe"], 2), "DD", round(v1["max_drawdown"], 4),
          "islem", v1["trades"], "| 2x", round(v2["total_return"], 4), "| aday", chk["aday"], flush=True)
cikti.write_text(json.dumps(temiz(sonuc), ensure_ascii=False, indent=1), encoding="utf-8")
print("yazildi", cikti)
