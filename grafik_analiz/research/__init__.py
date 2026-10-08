"""Kârlı strateji araştırması: ön kayıtlı protokol, dönem kilitli veri, ortak backtest.

Kullanım:

    from grafik_analiz.research import StrategySpec, evaluate, assert_causal, candidate_check

    def sinyal(data, funding, hizli=20, yavas=100):
        out = {}
        for leg, df in data.items():
            hizli_ort = df["close"].rolling(hizli).mean()
            yavas_ort = df["close"].rolling(yavas).mean()
            out[leg] = (hizli_ort > yavas_ort).astype(float)
        return out

    spec = StrategySpec("ma_kesisim", "trend", "1d", (("spot", "BTCUSDT"),), sinyal, {"hizli": 20, "yavas": 100})
    assert_causal(spec)
    sonuc = evaluate(spec)            # dev_train ve dev_valid, 1× ve 2× maliyet
    candidate_check(sonuc)
"""

from .backtest import LegResult, backtest_leg, combine
from .data import HoldoutLocked, load, load_funding, lock_holdout, unlock_holdout
from .evaluate import RunResult, StrategySpec, assert_causal, candidate_check, evaluate, holdout_check, run
from .metrics import daily_returns, deflated_sharpe, summarize
from .protocol import COSTS, DEV_END, DEV_TRAIN_END, HOLDOUT_END, HOLDOUT_START, PERIODS

__all__ = [
    "COSTS",
    "DEV_END",
    "DEV_TRAIN_END",
    "HOLDOUT_END",
    "HOLDOUT_START",
    "PERIODS",
    "HoldoutLocked",
    "LegResult",
    "RunResult",
    "StrategySpec",
    "assert_causal",
    "backtest_leg",
    "candidate_check",
    "combine",
    "daily_returns",
    "deflated_sharpe",
    "evaluate",
    "holdout_check",
    "load",
    "load_funding",
    "lock_holdout",
    "run",
    "summarize",
    "unlock_holdout",
]
