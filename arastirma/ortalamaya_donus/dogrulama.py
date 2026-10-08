"""Dondurulan yapılandırmaların TEK SEFERLİK dev_valid değerlendirmesi.

Dondurma: 4 yapılandırma (grafik_analiz/strategies/ortalamaya_donus.py: specs()),
parametreleri yalnız dev_train sonuçlarıyla seçildi (tarama1–7). Bu betik bir kez
çalıştırılır: assert_causal → evaluate(spec) (dev_train + dev_valid, 1× ve 2×)
→ candidate_check. Ardından al-tut karşılaştırması (deftere yazılmaz) ve
Deflated Sharpe hesaplanır.
"""
import json
import pickle

import numpy as np
import pandas as pd

from grafik_analiz.research import assert_causal, candidate_check, deflated_sharpe, evaluate
from grafik_analiz.research.evaluate import StrategySpec
from grafik_analiz.research.ledger import trials
from grafik_analiz.strategies.ortalamaya_donus import COINS, FAMILY, specs
from ortak import KLASOR


def al_tut(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}


def main():
    sonuc = {}
    for spec in specs():
        assert_causal(spec)
        res = evaluate(spec)
        chk = candidate_check(res)
        sonuc[spec.name] = {"params": spec.params, "interval": spec.interval, "legs": spec.legs, "causal": True, "results": res, "check": chk}
        v1 = res["dev_valid"][1.0]
        v2 = res["dev_valid"][2.0]
        print(spec.name, "aday" if chk["aday"] else "aday değil", chk)
        print("  dev_valid 1x ret=%.4f sh=%.3f dd=%.4f n=%s | 2x ret=%.4f" % (v1["total_return"], v1["sharpe"], v1["max_drawdown"], v1.get("trades"), v2["total_return"]))

    # Al-tut (karşılaştırma; deney defterine yazılmaz)
    bh = {}
    for market in ("futures", "spot"):
        for uni in ("PORT3",) + COINS:
            legs = tuple((market, c) for c in COINS) if uni == "PORT3" else ((market, uni),)
            for interval in ("1h", "15m"):
                spec = StrategySpec(f"al_tut_{market}_{uni}_{interval}", FAMILY, interval, legs, al_tut)
                r = evaluate(spec, record=False)
                bh[spec.name] = r
    # Deflated Sharpe
    t = trials(FAMILY)
    t = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
    sh = pd.Series([o.get("sharpe") for o in t["olcu"]], dtype=float).dropna()
    n_trials = len(t)
    var = float(sh.var())
    for name, s in sonuc.items():
        v = s["results"]["dev_valid"][1.0]
        s["dsr"] = deflated_sharpe(v["sharpe"], v["days"], n_trials, var, v["skew"], v["kurtosis"])
        s["dsr_inputs"] = {"n_trials": n_trials, "sr_var": var, "skew": v["skew"], "kurtosis": v["kurtosis"], "days": v["days"]}
        print(name, "DSR=%.4f" % s["dsr"], s["dsr_inputs"])
    with open(KLASOR / "dondurulmus_sonuclar.pkl", "wb") as fh:
        pickle.dump({"sonuc": {k: {kk: vv for kk, vv in v.items()} for k, v in sonuc.items()}, "al_tut": bh}, fh)

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(x) for x in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return o

    (KLASOR / "dondurulmus_sonuclar.json").write_text(json.dumps(clean({"sonuc": sonuc, "al_tut": bh}), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
