"""Arama yardımcıları (t2_limit_gun_ici).

Her yapılandırma `evaluate(spec, windows=("dev_train",), ...)` ile deftere yazılır.
Ardından aynı sinyallerle, veri ve sinyaller DEV_TRAIN_END'de kesilerek, dev_train
penceresinde tanı ölçüleri hesaplanır: işlem başına brüt/net kenar, dolum oranı,
maker payı, ters seçilim (dolan ve dolmayan giriş emirlerinin "piyasa emriyle
girilseydi" getirisi), yıllık getiri ve bacak getirisi. dev_valid'e bakılmaz.
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research.backtest import backtest_leg
from grafik_analiz.research.evaluate import evaluate, load_data
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies import t2_limit_gun_ici as lg

assert PROTOCOL_VERSION == "2", "GRAFIK_ANALIZ_PROTOKOL=2 gerekli"

HERE = Path(__file__).resolve().parent
_CACHE: dict = {}


def _key(data, params):
    return (
        json.dumps(params, sort_keys=True, default=str),
        tuple((leg, len(df), int(df.index[-1].value)) for leg, df in sorted(data.items())),
    )


def memo_signal(data, funding, **params):
    """`lg.sinyal` ile aynı çıktı; ayrıca emir kayıtlarını tanı için saklar."""
    key = _key(data, params)
    if key not in _CACHE:
        _CACHE.clear()
        out, rec = {}, {}
        for leg, df in data.items():
            tgt, lim, orders, exits, posv = lg.leg_orders(df, params)
            out[leg] = pd.DataFrame({"target": tgt, "limit": lim}, index=df.index)
            rec[leg] = (orders, exits, posv)
        _CACHE[key] = (out, rec)
    return _CACHE[key][0]


def _records(data, params):
    return _CACHE[_key(data, params)][1]


FIELDS = [
    "name", "interval", "params", "total_return", "sharpe", "max_drawdown", "trades", "alfa", "beta", "alfa_t",
    "exposure", "gross_pt_bps", "net_pt_bps", "win", "avg_bars", "maker_giris", "maker_cikis", "orders", "fill_rate",
    "mo_fill_mkt_bps", "mo_miss_mkt_bps", "mo_all_mkt_bps", "mo_fill_lim_bps", "iyilesme_bps",
    "y2020", "y2021", "y2022", "y2023", "y2024", "leg_BTC", "leg_ETH", "leg_SOL", "ret_2x", "sharpe_2x", "sec",
]


def degerlendir(name: str, interval: str, csv_name: str, cost2: bool = False, universe: str = "PORT3", **params) -> dict:
    spec = lg.make_spec(name, interval, universe=universe, **params)
    spec.signal_fn = memo_signal
    t0 = time.time()
    mults = (1.0, 2.0) if cost2 else (1.0,)
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=mults)
    m = res["dev_train"][1.0]
    data, funding = load_data(spec, "dev")
    sigs = memo_signal(data, funding, **params)
    rec = _records(data, params)
    H = int(params.get("H", 12)) if "H" in params else 12

    row = {
        "name": spec.name,
        "interval": interval,
        "params": json.dumps(params, sort_keys=True),
        **{k: m.get(k) for k in ("total_return", "sharpe", "max_drawdown", "trades", "alfa", "beta", "alfa_t", "exposure", "avg_bars")},
    }
    if cost2:
        row["ret_2x"] = res["dev_train"][2.0].get("total_return")
        row["sharpe_2x"] = res["dev_train"][2.0].get("sharpe")

    w = spec.leg_weights()
    g_all, n_all = [], []
    n_ord = n_fill = 0
    mk_in = mk_in_n = 0
    mk_out = mk_out_n = 0
    mo_fill, mo_miss, mo_lim, impr = [], [], [], []
    port = None
    for leg, df in data.items():
        cut = df.index < DEV_TRAIN_END
        dfc = df[cut]
        sc = sigs[leg][cut]
        fu = funding.get(leg[1])
        fu = fu[fu.index < DEV_TRAIN_END] if fu is not None else None
        lr = backtest_leg(dfc, sc, market=leg[0], symbol=leg[1], funding=fu)
        row["leg_" + leg[1][:3]] = float((1.0 + lr.net).prod() - 1.0)
        r = w[leg] * lr.net
        port = r if port is None else port.add(r, fill_value=0.0)
        t = lr.trades
        g_all.append(t["gross_return"].to_numpy())
        n_all.append(t["net_return"].to_numpy())
        orders, exits, posv = rec[leg]
        # Motorun pozisyonu backtest'inkiyle aynı olmalı.
        if not np.allclose(posv[: len(dfc)], lr.position.to_numpy()):
            raise AssertionError(f"{spec.name} {leg}: motor pozisyonu backtest ile uyuşmuyor")
        nb = len(dfc)
        o = dfc["open"].to_numpy(float)
        c = dfc["close"].to_numpy(float)
        for (j, side, lp, filled, px, mkt, *_) in orders:
            if j + H - 1 >= nb:
                continue
            n_ord += 1
            mo = side * (c[j + H - 1] / o[j] - 1.0)
            if filled:
                n_fill += 1
                mk_in_n += 1
                mk_in += 0 if mkt else 1
                mo_fill.append(mo)
                mo_lim.append(side * (c[j + H - 1] / px - 1.0))
                impr.append(side * (o[j] / px - 1.0))
            else:
                mo_miss.append(mo)
        for (j, side, ep, px, mkt) in exits:
            if j >= nb:
                continue
            mk_out_n += 1
            mk_out += 0 if mkt else 1
    g = np.concatenate(g_all) if g_all else np.array([])
    nn = np.concatenate(n_all) if n_all else np.array([])
    yearly = (1.0 + port).groupby(port.index.year).prod() - 1.0
    for y in range(2020, 2025):
        row[f"y{y}"] = float(yearly.get(y, float("nan")))
    mean = lambda a: float(np.mean(a) * 1e4) if len(a) else float("nan")  # noqa: E731
    row.update(
        {
            "gross_pt_bps": mean(g),
            "net_pt_bps": mean(nn),
            "win": float(np.mean(nn > 0)) if len(nn) else float("nan"),
            "maker_giris": mk_in / mk_in_n if mk_in_n else float("nan"),
            "maker_cikis": mk_out / mk_out_n if mk_out_n else float("nan"),
            "orders": n_ord,
            "fill_rate": n_fill / n_ord if n_ord else float("nan"),
            "mo_fill_mkt_bps": mean(mo_fill),
            "mo_miss_mkt_bps": mean(mo_miss),
            "mo_all_mkt_bps": mean(mo_fill + mo_miss),
            "mo_fill_lim_bps": mean(mo_lim),
            "iyilesme_bps": mean(impr),
            "sec": round(time.time() - t0, 1),
        }
    )
    path = HERE / csv_name
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            wr.writeheader()
        wr.writerow(row)
    _print(row)
    return row


def _f(x, pct=True, w=7):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return " " * (w - 3) + "nan"
    return f"{x * 100:+{w}.1f}%" if pct else f"{x:+{w}.2f}"


def _print(r: dict) -> None:
    yrs = " ".join(_f(r.get(f"y{y}"), w=5) for y in range(2020, 2025))
    s = (
        f"{r['name'][-58:]:58s} ret {_f(r['total_return'])} sh {_f(r['sharpe'], False, 5)} dd {_f(r['max_drawdown'], w=5)} "
        f"n {int(r['trades'] or 0):6d} a {_f(r['alfa'], w=6)} b {_f(r['beta'], False, 5)} t {_f(r['alfa_t'], False, 5)} "
        f"g/t {r['gross_pt_bps']:+6.1f} n/t {r['net_pt_bps']:+6.1f} fill {r['fill_rate'] if r['fill_rate']==r['fill_rate'] else float('nan'):.3f} "
        f"mkF {r['mo_fill_mkt_bps']:+6.1f} mkM {r['mo_miss_mkt_bps']:+6.1f} limF {r['mo_fill_lim_bps']:+6.1f} "
        f"mkr {r['maker_giris']:.2f}/{r['maker_cikis']:.2f} | {yrs}"
    )
    if r.get("ret_2x") is not None:
        s += f" | 2x {_f(r['ret_2x'])} sh2 {_f(r['sharpe_2x'], False, 5)}"
    s += f" | {_f(r.get('leg_BTC'), w=5)} {_f(r.get('leg_ETH'), w=5)} {_f(r.get('leg_SOL'), w=5)} [{r['sec']}s]"
    print(s, flush=True)


def done(csv_name: str) -> set:
    path = HERE / csv_name
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as fh:
        return {row["name"] for row in csv.DictReader(fh)}
