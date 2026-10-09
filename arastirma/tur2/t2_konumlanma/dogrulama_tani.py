"""Dondurma ve tek seferlik iç doğrulamadan SONRA betimleyici tanı (deftere yazmaz).

Dondurulan 5 yapılandırmanın iç doğrulama dönemindeki sonucunu coin, yön ve
yarıyıl bazında ayırır; brüt getiri (maliyet ve fonlama öncesi) ile neti
karşılaştırır. Hiçbir parametre ya da seçim bu çıktıya göre değiştirilmez.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.backtest import backtest_leg
from grafik_analiz.research.evaluate import benchmark_daily, compute_signals, load_data
from grafik_analiz.research.metrics import alpha_beta, daily_returns, sharpe, window
from grafik_analiz.research.protocol import PERIODS, PROTOCOL_VERSION
from grafik_analiz.strategies.t2_konumlanma import specs


def comp(r: pd.Series) -> float:
    return float((1 + r).prod() - 1)


def main() -> None:
    assert PROTOCOL_VERSION == "2"
    start, end = PERIODS["dev_valid"]
    for spec in specs():
        data, funding = load_data(spec)
        sig = compute_signals(spec, data, funding)
        bench = window(benchmark_daily(spec), start, end)
        w = spec.leg_weights()
        print(f"\n== {spec.name}")
        total_net = None
        total_gross = None
        for leg in spec.legs:
            s = sig[leg]
            res = backtest_leg(data[leg], s, market="futures", symbol=leg[1], funding=funding.get(leg[1]))
            net = window(res.net, start, end)
            gross = window(res.gross, start, end)
            total_net = net * w[leg] if total_net is None else total_net.add(net * w[leg], fill_value=0.0)
            total_gross = gross * w[leg] if total_gross is None else total_gross.add(gross * w[leg], fill_value=0.0)
            pos = window(res.position, start, end)
            ab = alpha_beta(daily_returns(net), bench)
            long_share = float((pos > 0).mean())
            short_share = float((pos < 0).mean())
            long_net = comp(net[pos > 0])
            short_net = comp(net[pos < 0])
            print(
                f"  {leg[1]}: net {comp(net):+.3f} brüt {comp(gross):+.3f} sh {sharpe(daily_returns(net)):+.2f} "
                f"alfa {ab['alfa']:+.3f} beta {ab['beta']:+.2f} | uzun %{100 * long_share:.0f} (net {long_net:+.3f}) "
                f"kısa %{100 * short_share:.0f} (net {short_net:+.3f})"
            )
        halves = total_net.groupby([total_net.index.year, (total_net.index.month - 1) // 6]).apply(comp)
        print("  sepet net {:+.3f}, brüt {:+.3f}".format(comp(total_net), comp(total_gross)))
        print("  yarıyıl net: " + ", ".join(f"{y}-Y{h + 1} {v:+.3f}" for (y, h), v in halves.items()))
    b = window(benchmark_daily(specs()[0]), start, end)
    hb = b.groupby([b.index.year, (b.index.month - 1) // 6]).apply(comp)
    print("\nal-tut yarıyıl: " + ", ".join(f"{y}-Y{h + 1} {v:+.3f}" for (y, h), v in hb.items()))


if __name__ == "__main__":
    main()
