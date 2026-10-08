"""Al-tut kıyası (strateji değil; deney defterine yazılmaz, deneme sayılmaz).

Kullanım:  python arastirma/trend/al_tut.py dev_train [dev_valid]

Her bacakta sürekli 1.0 pozisyon. Aynı backtest motoru ve maliyetlerle
(giriş maliyeti dahil) hesaplanır. dev_valid yalnızca dondurmadan SONRA istenir.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from grafik_analiz.research import StrategySpec, evaluate
from grafik_analiz.strategies.trend import legs_for

HERE = Path(__file__).resolve().parent


def hold(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}


def main(windows: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for market in ("spot", "futures"):
        for universe in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "PORT3"):
            for interval in ("1d", "4h"):
                spec = StrategySpec(f"al_tut_{market}_{universe}_{interval}", "trend_benchmark", interval, legs_for(market, universe), hold)
                res = evaluate(spec, windows=windows, cost_multipliers=(1.0,), record=False)
                for w in windows:
                    m = res[w][1.0]
                    rows.append(
                        {
                            "window": w,
                            "market": market,
                            "universe": universe,
                            "interval": interval,
                            "ret": m.get("total_return"),
                            "cagr": m.get("cagr"),
                            "sharpe": m.get("sharpe"),
                            "maxdd": m.get("max_drawdown"),
                            "vol": m.get("volatility"),
                            "funding": m.get("total_funding"),
                            "start": m.get("start"),
                            "days": m.get("days"),
                        }
                    )
    df = pd.DataFrame(rows)
    df.to_csv(HERE / f"al_tut_{'_'.join(windows)}.csv", index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(main(tuple(sys.argv[1:]) or ("dev_train",)).round(3).to_string())
