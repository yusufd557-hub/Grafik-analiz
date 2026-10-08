"""Görülmemiş dönem testi: finalistler 01.07.2025–30.09.2026'da bir kez ölçülür.

Finalistler `finalist_secimi.json` dosyasından okunur. Sonuç dosyası varsa
betik çalışmaz: test tek seferliktir (protokol, docs/PROTOKOL.md).

Çalıştırma:
    GRAFIK_ANALIZ_ARASTIRMA=<veri> python arastirma/holdout_testi.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from grafik_analiz.research import unlock_holdout
from grafik_analiz.research.evaluate import StrategySpec, evaluate, holdout_check
from grafik_analiz.research.protocol import STRESS_MULTIPLIER
from grafik_analiz.strategies import all_specs

HERE = Path(__file__).resolve().parent
SECIM = HERE / "finalist_secimi.json"
SONUC = HERE / "holdout_sonuc.json"


def _hold(data, funding):
    out = {}
    for leg, df in data.items():
        target = pd.Series(1.0, index=df.index)
        if leg[0] == "futures" and leg[1] in funding and not funding[leg[1]].empty:
            target[df.index < funding[leg[1]].index[0]] = 0.0
        out[leg] = target
    return out


def benchmark(spec: StrategySpec) -> StrategySpec:
    """Aynı piyasa, zaman dilimi ve bacaklarla eşit ağırlıklı al-tut."""
    return StrategySpec(f"al_tut_{spec.name}", "_kiyas", spec.interval, spec.legs, _hold, {}, spec.weights)


def main() -> None:
    if SONUC.exists():
        raise SystemExit("görülmemiş dönem testi zaten yapıldı; tekrar çalıştırılmaz")
    secim = json.loads(SECIM.read_text(encoding="utf-8"))
    finalistler = secim["finalistler"]
    specs = {s.name: s for s in all_specs()}
    n = len(finalistler)

    unlock_holdout(
        f"Protokol sürüm 1, tek seferlik görülmemiş dönem testi: {n} finalist "
        f"({', '.join(finalistler)}); seçim kuralı FINALISTLER.md, seçim finalist_secimi.json"
    )

    sonuc = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "finalistler": {}}
    for name in finalistler:
        spec = specs[name]
        res = evaluate(spec, windows=("holdout",), cost_multipliers=(1.0, STRESS_MULTIPLIER), record=True)
        kontrol = holdout_check(res, n)
        kiyas = evaluate(benchmark(spec), windows=("holdout",), cost_multipliers=(1.0,), record=False)
        sonuc["finalistler"][name] = {
            "aile": spec.family,
            "olcu_1x": res["holdout"][1.0],
            "olcu_2x": res["holdout"][STRESS_MULTIPLIER],
            "kontrol": kontrol,
            "al_tut": kiyas["holdout"][1.0],
        }
        m = res["holdout"][1.0]
        print(
            f"{name}: net {m['total_return']:+.4f}, 2x {res['holdout'][STRESS_MULTIPLIER]['total_return']:+.4f}, "
            f"Sharpe {m['sharpe']:.2f}, işlem {m.get('trades')}, p {m['p_value']:.4f}, "
            f"Seviye1 {kontrol['seviye1_gecti']}, Seviye2 {kontrol['seviye2_gecti']}, "
            f"al-tut {kiyas['holdout'][1.0]['total_return']:+.4f}",
            flush=True,
        )
    SONUC.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
