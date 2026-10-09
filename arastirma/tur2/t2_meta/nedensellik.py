"""Dondurulan yapılandırmaların ileri bakış denetimi (performans yazdırmaz).

1. `assert_causal(spec)` varsayılan kesimler (0,55 / 0,8 / 0,97) ve ek kesimler.
2. Hedefli kesimler: aylık yeniden eğitimden hemen sonra (ay başı + 1 bar) ve rastgele seçilmiş
   pozisyon değişim barlarında; kesik veriyle üretilen sinyal tam veriyle üretilenle aynı olmalı.
"""
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402,F401
from grafik_analiz.research.evaluate import assert_causal, compute_signals, load_data  # noqa: E402
from grafik_analiz.strategies import t2_meta as tm  # noqa: E402


def hedefli(spec, cuts) -> int:
    data, funding = load_data(spec, "dev")
    full = compute_signals(spec, data, funding)
    for cut in cuts:
        pd_ = {leg: f[f.index <= cut] for leg, f in data.items()}
        pf = {s: f[f.index <= cut] for s, f in funding.items()}
        part = compute_signals(spec, pd_, pf)
        for leg in spec.legs:
            a = full[leg].reindex(pd_[leg].index).astype(float)
            b = part[leg].reindex(pd_[leg].index).astype(float)
            diff = (a - b).abs().fillna(np.inf)
            if (diff > 1e-9).any():
                raise AssertionError(f"{spec.name} {leg}: kesim {cut} → {diff[diff > 1e-9].index[0]} farklı")
    return len(cuts)


if __name__ == "__main__":
    rng = np.random.default_rng(7)
    for spec in tm.specs():
        t0 = time.time()
        assert_causal(spec)
        assert_causal(spec, fractions=(0.3, 0.5, 0.65, 0.75, 0.9, 0.995))
        data, funding = load_data(spec, "dev")
        idx = data[spec.legs[0]].index
        step = idx[1] - idx[0]
        cuts = [pd.Timestamp(t, tz="UTC") + step for t in ("2022-06-01", "2024-03-01", "2025-05-01", "2026-02-01")]
        sig = compute_signals(spec, data, funding)
        changes = []
        for leg in spec.legs:
            s = sig[leg]
            ch = s.index[(s != s.shift(1)) & (s.index > idx[int(len(idx) * 0.3)])]
            changes.extend(ch)
        changes = sorted(set(changes))
        pick = [changes[i] for i in sorted(rng.choice(len(changes), size=min(6, len(changes)), replace=False))]
        n = hedefli(spec, cuts + pick)
        print(f"GECTI {spec.name}: assert_causal 9 kesim + {n} hedefli kesim ({time.time() - t0:.0f}s)", flush=True)
    print("BITTI", flush=True)
