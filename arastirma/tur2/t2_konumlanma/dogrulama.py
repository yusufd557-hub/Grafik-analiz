"""Dondurulan yapılandırmaların tek seferlik iç doğrulama (dev_valid) değerlendirmesi.

Her spec için bir kez `evaluate(spec)` (dev_train + dev_valid, 1× ve 2×),
`candidate_check`, al-tut kıyası ve Deflated Sharpe. Bu betik yalnız bir kez
çalıştırılır; sonuç `dondurulmus_sonuclar.json` dosyasına yazılır.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import benchmark_daily, candidate_check, evaluate
from grafik_analiz.research.ledger import trials
from grafik_analiz.research.metrics import deflated_sharpe, sharpe, window
from grafik_analiz.research.protocol import PERIODS, PROTOCOL_VERSION
from grafik_analiz.strategies.t2_konumlanma import FAMILY, specs

HERE = Path(__file__).resolve().parent
OUT = HERE / "dondurulmus_sonuclar.json"


def bench_stats(spec) -> dict:
    b = benchmark_daily(spec)
    out = {}
    for w in ("dev_train", "dev_valid"):
        start, end = PERIODS[w]
        d = window(b, start, end).dropna()
        eq = (1 + d).cumprod()
        out[w] = {
            "total_return": float(eq.iloc[-1] - 1),
            "sharpe": sharpe(d),
            "max_drawdown": float((eq / eq.cummax() - 1).min()),
            "start": str(d.index[0]),
            "end": str(d.index[-1]),
        }
    return out


def main() -> None:
    assert PROTOCOL_VERSION == "2"
    assert not OUT.exists(), "iç doğrulama zaten yapıldı; tekrar çalıştırılmaz"
    frozen = json.loads((HERE / "dondurma.json").read_text(encoding="utf-8"))["secilen"]
    sp = specs()
    assert [s.name for s in sp] == [r["strateji"] for r in frozen]
    for s, r in zip(sp, frozen):
        assert s.params == r["parametreler"] and s.interval == r["dilim"], s.name
    results = {}
    for spec in sp:
        res = evaluate(spec)
        cc = candidate_check(res)
        results[spec.name] = {
            "params": spec.params,
            "interval": spec.interval,
            "legs": [list(l) for l in spec.legs],
            "sonuc": {w: {str(k): v for k, v in m.items()} for w, m in res.items()},
            "candidate_check": cc,
        }
        print(f"{spec.name}: aday={cc['aday']}", flush=True)
    bench = bench_stats(sp[0])

    t = trials(FAMILY)
    tr = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
    sh = pd.to_numeric(tr["olcu"].apply(lambda o: o.get("sharpe")), errors="coerce")
    n_trials = len(tr)
    var = float(np.nanvar(sh.to_numpy(dtype=float), ddof=1))
    start, end = PERIODS["dev_valid"]
    n_days = int((end - start).days)
    dsr = {"deneme_sayisi": n_trials, "benzersiz_yapilandirma": int(tr["strateji"].nunique()), "sharpe_varyansi": var, "gun": n_days, "stratejiler": {}}
    for name, r in results.items():
        v = r["sonuc"]["dev_valid"]["1.0"]
        d = deflated_sharpe(v["sharpe"], n_days, n_trials, var, v["skew"], v["kurtosis"]) if v.get("sharpe") is not None else float("nan")
        dsr["stratejiler"][name] = {"sharpe": v.get("sharpe"), "skew": v.get("skew"), "kurtosis": v.get("kurtosis"), "dsr": d}
    OUT.write_text(json.dumps({"sonuclar": results, "al_tut": bench, "dsr": dsr}, ensure_ascii=False, indent=1, default=float), encoding="utf-8")

    keys = ("total_return", "sharpe", "max_drawdown", "trades", "alfa", "beta", "alfa_t", "p_value", "exposure")
    for name, r in results.items():
        print(f"\n== {name}")
        for w in ("dev_train", "dev_valid"):
            for m in ("1.0", "2.0"):
                x = r["sonuc"][w][m]
                print(f"  {w:9s} {m}x  " + "  ".join(f"{k} {x.get(k):+.4f}" if isinstance(x.get(k), float) else f"{k} {x.get(k)}" for k in keys))
        print("  candidate_check:", r["candidate_check"])
        print(f"  DSR: {dsr['stratejiler'][name]['dsr']:.4f}")
    print("\nal-tut (BTC/ETH/SOL vadeli eşit ağırlık, brüt):", json.dumps(bench, indent=1))
    print(f"DSR: deneme {n_trials} (benzersiz {dsr['benzersiz_yapilandirma']}), Sharpe varyansı {var:.4f}, gün {n_days}")


if __name__ == "__main__":
    main()
