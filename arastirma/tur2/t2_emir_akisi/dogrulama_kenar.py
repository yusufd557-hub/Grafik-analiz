"""Betimleyici (dev_valid değerlendirmesinden sonra; parametre değişmez, deftere yazılmaz):
dondurulan yapılandırmalarda işlem başına brüt kenar ve maliyet, dev_train ve dev_valid."""
import numpy as np

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import run
from grafik_analiz.strategies.t2_emir_akisi import specs

for spec in specs():
    r = run(spec, "dev", 1.0)
    out = []
    for w in ("dev_train", "dev_valid"):
        s, e = protocol.PERIODS[w]
        g, nn = [], []
        for leg, lr in r.legs.items():
            t = lr.trades
            if s is not None:
                t = t[t["entry_time"] >= s]
            t = t[t["entry_time"] < e]
            g.append(t["gross_return"].to_numpy())
            nn.append(t["net_return"].to_numpy())
        g, nn = np.concatenate(g), np.concatenate(nn)
        out.append(f"{w}: işlem {len(g)}, brüt {np.mean(g)*1e4:+.1f} bps, net {np.mean(nn)*1e4:+.1f} bps, "
                   f"maliyet+fonlama {(np.mean(g)-np.mean(nn))*1e4:.1f} bps, kazanan {np.mean(nn>0):.2f}")
    print(spec.name, "|", " | ".join(out), flush=True)
