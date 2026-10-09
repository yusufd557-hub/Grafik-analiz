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

**Limit emir (isteğe bağlı):** Strateji, Series yerine `target` ve `limit`
sütunlu bir DataFrame döndürürse, `limit` dolu olan barlarda pozisyon değişimi
bir sonraki barda limit emirle denenir. Emir, verildiği anda piyasa fiyatının
öbür tarafındaysa (alış limiti açılışın üstünde, satış limiti altında) hemen
piyasa emri gibi işler. Değilse yalnız fiyat limitin `LIMIT_PENETRATION`
ötesine geçerse limit fiyattan dolar ve maker komisyonu ödenir; dolmazsa bar
sonunda iptal edilir ve pozisyon değişmez. `limit` boş olan barlarda emir
piyasa emridir.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..data import FUTURES, SPOT
from .protocol import COSTS, LIMIT_PENETRATION, MAKER_COSTS, MAX_LEVERAGE, Costs


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
    if isinstance(target, pd.DataFrame):
        return _backtest_limit(frame, target, market, symbol, funding, costs, cost_multiplier, max_leverage)
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


def _backtest_limit(
    frame: pd.DataFrame,
    orders: pd.DataFrame,
    market: str,
    symbol: str,
    funding: pd.DataFrame | None,
    costs: Costs | None,
    cost_multiplier: float,
    max_leverage: float | None,
) -> LegResult:
    """Limit emirli sıralı simülasyon (bkz. modül açıklaması)."""
    taker = (costs or COSTS[market]).scaled(cost_multiplier)
    maker = MAKER_COSTS[market].scaled(cost_multiplier)
    lev = MAX_LEVERAGE[market] if max_leverage is None else max_leverage
    index = frame.index
    n = len(index)
    lower = -lev if market == FUTURES else 0.0
    tgt = orders["target"].reindex(index).astype(float).fillna(0.0).clip(lower, lev).to_numpy()
    lim = orders["limit"].reindex(index).astype(float).to_numpy() if "limit" in orders else np.full(n, np.nan)

    o = frame["open"].to_numpy(dtype=float)
    h = frame["high"].to_numpy(dtype=float)
    lo = frame["low"].to_numpy(dtype=float)
    c = frame["close"].to_numpy(dtype=float)
    nxt = np.empty(n)
    nxt[:-1] = o[1:]
    if n:
        nxt[-1] = c[-1]

    pos_end = np.zeros(n)
    gross = np.zeros(n)
    cost = np.zeros(n)
    pos = 0.0
    for i in range(n):
        desired = tgt[i - 1] if i > 0 else 0.0
        limit = lim[i - 1] if i > 0 else np.nan
        change = desired - pos
        if change == 0.0:
            gross[i] = pos * (nxt[i] / o[i] - 1.0)
        elif np.isnan(limit) or (change > 0 and limit >= o[i]) or (change < 0 and limit <= o[i]):
            # Piyasa emri ya da hemen işleyen limit: açılışta, taker maliyetiyle.
            cost[i] = abs(change) * taker.per_side
            pos = desired
            gross[i] = pos * (nxt[i] / o[i] - 1.0)
        else:
            filled = lo[i] < limit * (1.0 - LIMIT_PENETRATION) if change > 0 else h[i] > limit * (1.0 + LIMIT_PENETRATION)
            if filled:
                before = 1.0 + pos * (limit / o[i] - 1.0)
                after = 1.0 + desired * (nxt[i] / limit - 1.0)
                gross[i] = before * after - 1.0
                cost[i] = abs(change) * maker.per_side
                pos = desired
            else:
                gross[i] = pos * (nxt[i] / o[i] - 1.0)
        pos_end[i] = pos

    pos_series = pd.Series(pos_end, index=index)
    gross_s = pd.Series(gross, index=index)
    cost_s = pd.Series(cost, index=index)
    fund = pd.Series(0.0, index=index)
    if market == FUTURES and funding is not None and not funding.empty and n:
        fund = _funding_charges(index, pos_end, funding)
    net = gross_s - cost_s - fund
    trades = _trades(index, pos_series, gross_s, fund, taker.per_side)
    return LegResult(market, symbol, pos_series, gross_s, cost_s, fund, net, trades)


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
