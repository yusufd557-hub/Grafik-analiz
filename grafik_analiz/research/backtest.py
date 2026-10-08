"""İleri bakışsız işlem simülasyonu.

Kurallar (bütün stratejiler için aynı):

- Strateji, t barının **kapanışında** bilinen veriyle hedef pozisyonu söyler
  (sermayenin katı; spotta 0…1, vadelide −1…1).
- Pozisyon t+1 barının **açılışında** alınır ve t+2 açılışına kadar tutulur.
  Bar getirisi açılıştan bir sonraki açılışa ölçülür; son bar kapanışta
  değerlenir.
- Her pozisyon değişiminde değişen tutar × (komisyon + kayma) maliyet düşülür.
- Vadelide fonlama: fonlama anında açık pozisyon × oran ödenir (uzun pozisyon
  pozitif oranda öder, kısa pozisyon alır). Fonlama anı bir barın açılışına denk
  gelirse o açılıştaki işlemden **önceki** pozisyon esas alınır.
- Spotta açığa satış yoktur: negatif hedef 0'a kırpılır.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data import FUTURES, SPOT
from .protocol import COSTS, MAX_LEVERAGE, Costs


@dataclass
class LegResult:
    market: str
    symbol: str
    position: pd.Series
    """Bar boyunca tutulan pozisyon (açılış t → açılış t+1)."""
    gross: pd.Series
    cost: pd.Series
    funding: pd.Series
    net: pd.Series
    trades: pd.DataFrame


def backtest_leg(
    frame: pd.DataFrame,
    target: pd.Series,
    market: str = SPOT,
    symbol: str = "",
    funding: pd.DataFrame | None = None,
    costs: Costs | None = None,
    cost_multiplier: float = 1.0,
    max_leverage: float | None = None,
) -> LegResult:
    if market not in (SPOT, FUTURES):
        raise ValueError(f"bilinmeyen piyasa: {market}")
    costs = (costs or COSTS[market]).scaled(cost_multiplier)
    lev = MAX_LEVERAGE[market] if max_leverage is None else max_leverage
    index = frame.index

    tgt = pd.Series(target, dtype=float).reindex(index).fillna(0.0)
    lower = -lev if market == FUTURES else 0.0
    tgt = tgt.clip(lower, lev)
    pos = tgt.shift(1).fillna(0.0)

    open_ = frame["open"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    ret = np.empty(len(open_))
    ret[:-1] = open_[1:] / open_[:-1] - 1.0
    if len(open_):
        ret[-1] = close[-1] / open_[-1] - 1.0
    ret = pd.Series(ret, index=index)

    gross = pos * ret
    turnover = (pos - pos.shift(1).fillna(0.0)).abs()
    cost = turnover * costs.per_side

    fund = pd.Series(0.0, index=index)
    if market == FUTURES and funding is not None and not funding.empty and len(index):
        fund = _funding_charges(index, pos.to_numpy(), funding)

    net = gross - cost - fund
    trades = _trades(index, pos, gross, fund, costs.per_side)
    return LegResult(market, symbol, pos, gross, cost, fund, net, trades)


def _funding_charges(index: pd.DatetimeIndex, pos: np.ndarray, funding: pd.DataFrame) -> pd.Series:
    charges = np.zeros(len(index))
    step = index[-1] - index[-2] if len(index) > 1 else pd.Timedelta(0)
    times = funding.index
    inside = (times >= index[0]) & (times < index[-1] + step)
    times = times[inside]
    rates = funding["funding_rate"].to_numpy(dtype=float)[inside]
    if len(times) == 0:
        return pd.Series(charges, index=index)
    bar = index.searchsorted(times, side="right") - 1
    at_open = index[bar] == times
    exposure_bar = np.where(at_open, bar - 1, bar)
    valid = exposure_bar >= 0
    exposure = np.zeros(len(times))
    exposure[valid] = pos[exposure_bar[valid]]
    np.add.at(charges, bar[valid], exposure[valid] * rates[valid])
    return pd.Series(charges, index=index)


def _trades(index: pd.DatetimeIndex, pos: pd.Series, gross: pd.Series, fund: pd.Series, per_side: float) -> pd.DataFrame:
    """Aynı yöndeki kesintisiz pozisyon dilimlerini işlem olarak listeler."""
    columns = ["entry_time", "exit_time", "direction", "bars", "size", "gross_return", "net_return"]
    sign = np.sign(pos.to_numpy())
    if not np.any(sign):
        return pd.DataFrame(columns=columns)
    change = np.flatnonzero(np.diff(np.concatenate([[0.0], sign])) != 0)
    rows = []
    g = gross.to_numpy()
    f = fund.to_numpy()
    p = pos.to_numpy()
    bounds = list(change) + [len(sign)]
    for a, b in zip(bounds[:-1], bounds[1:]):
        if sign[a] == 0:
            continue
        seg_gross = float(np.prod(1.0 + g[a:b]) - 1.0)
        seg_net_before_costs = float(np.prod(1.0 + g[a:b] - f[a:b]) - 1.0)
        size = float(np.abs(p[a:b]).max())
        entry_cost = abs(p[a]) * per_side
        # Veri sonunda hâlâ açık işlemde de çıkış maliyeti düşülür (ihtiyatlı).
        exit_cost = abs(p[b - 1]) * per_side
        rows.append(
            {
                "entry_time": index[a],
                "exit_time": index[b] if b < len(index) else index[-1],
                "direction": int(sign[a]),
                "bars": b - a,
                "size": size,
                "gross_return": seg_gross,
                "net_return": seg_net_before_costs - entry_cost - exit_cost,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def combine(legs: dict, weights: dict | None = None) -> pd.Series:
    """Bacakların net getirilerini sabit sermaye ağırlıklarıyla birleştirir.

    Her bar sabit ağırlığa dengelenmiş bir portföy varsayılır. Ağırlıklar
    verilmezse eşit dağıtılır (toplam 1).
    """
    keys = list(legs)
    if weights is None:
        weights = {k: 1.0 / len(keys) for k in keys}
    index = legs[keys[0]].net.index
    for k in keys[1:]:
        index = index.union(legs[k].net.index)
    total = pd.Series(0.0, index=index)
    for k in keys:
        total = total.add(weights[k] * legs[k].net.reindex(index).fillna(0.0), fill_value=0.0)
    return total
