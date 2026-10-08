"""Arama için ortak yardımcılar. Değerlendirme yalnızca harness `evaluate()` ile yapılır.

Arama sırasında yalnız dev_train penceresi kullanılır. Aynı yapılandırma iki kez
değerlendirilmez (deneme sayısı şişmesin diye yerel önbellek: tarama_sonuclari.jsonl).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import DEV_TRAIN_END, evaluate, run, summarize
from grafik_analiz.strategies.formasyon import make_spec

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "tarama_sonuclari.jsonl"

KISA = {"futures": "vad", "spot": "spo"}


def key_of(interval: str, market: str, universe: str, params: dict) -> str:
    return json.dumps({"interval": interval, "market": market, "universe": universe, **params}, sort_keys=True)


def done_keys() -> dict:
    out = {}
    if RESULTS.exists():
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["key"]] = row
    return out


def _fmt(v) -> str:
    if isinstance(v, (list, tuple)):
        return "+".join(_fmt(x) for x in v)
    return str(v)


def name_for(interval: str, market: str, universe: str, params: dict) -> str:
    parts = [params["yontem"], interval, KISA[market], universe]
    for k in sorted(params):
        if k == "yontem":
            continue
        v = params[k]
        if v is None or v is False or v == 0:
            continue
        parts.append(f"{k}={_fmt(v)}")
    return "_".join(parts)


def train_eval(interval: str, market: str, universe: str, params: dict, tag: str = "") -> dict:
    """dev_train'de 1× ve 2× maliyetle değerlendirir (deftere yazılır)."""
    key = key_of(interval, market, universe, params)
    cache = done_keys()
    if key in cache:
        return cache[key]
    name = name_for(interval, market, universe, params)
    spec = make_spec(name, interval, market, universe, params)
    t0 = time.time()
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))
    m1 = res["dev_train"][1.0]
    m2 = res["dev_train"][2.0]
    row = {
        "key": key,
        "tag": tag,
        "name": name,
        "interval": interval,
        "market": market,
        "universe": universe,
        "params": params,
        "ret1": m1.get("total_return"),
        "cagr1": m1.get("cagr"),
        "sharpe1": m1.get("sharpe"),
        "mdd1": m1.get("max_drawdown"),
        "trades": m1.get("trades"),
        "exposure": m1.get("exposure"),
        "win": m1.get("win_rate"),
        "pf": m1.get("profit_factor"),
        "avg_bars": m1.get("avg_bars"),
        "ret2": m2.get("total_return"),
        "sharpe2": m2.get("sharpe"),
        "costs1": m1.get("total_costs"),
        "fund1": m1.get("total_funding"),
        "start": m1.get("start"),
        "sec": round(time.time() - t0, 1),
    }
    row = {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in row.items()}
    with RESULTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def table(tag: str | None = None) -> pd.DataFrame:
    rows = list(done_keys().values())
    df = pd.DataFrame(rows)
    if tag is not None and not df.empty:
        df = df[df["tag"].str.startswith(tag)]
    return df


def train_diagnostics(interval: str, market: str, universe: str, params: dict, mults=(1.0,)) -> dict:
    """Defterde kayıtlı bir yapılandırma için yıllık, bacak ve yön bazlı tanı (yalnız dev_train).

    run() bütün dev kapsamını işler; sonuçlar ölçüm ÖNCESİNDE DEV_TRAIN_END'de kesilir.
    """
    key = key_of(interval, market, universe, params)
    if key not in done_keys():
        raise KeyError("tanı yalnız defterde kayıtlı yapılandırmalar için")
    spec = make_spec(name_for(interval, market, universe, params), interval, market, universe, params)
    out = {}
    for mult in mults:
        res = run(spec, scope="dev", cost_multiplier=mult)
        r = res.returns[res.returns.index < DEV_TRAIN_END]
        tr = res.trades[res.trades["entry_time"] < DEV_TRAIN_END]
        years = {}
        for y, ry in r.groupby(r.index.year):
            ty = tr[(tr["entry_time"].dt.year == y)]
            s = summarize(ry, ty)
            years[int(y)] = {"ret": s.get("total_return"), "sharpe": s.get("sharpe"), "trades": s.get("trades")}
        legs = {}
        for leg, lr in res.legs.items():
            nl = lr.net[lr.net.index < DEV_TRAIN_END]
            tl = lr.trades[lr.trades["entry_time"] < DEV_TRAIN_END]
            s = summarize(nl, tl)
            legs[f"{leg[0]}:{leg[1]}"] = {"ret": s.get("total_return"), "sharpe": s.get("sharpe"), "trades": s.get("trades"), "mdd": s.get("max_drawdown")}
        dirs = {}
        for d_, td in tr.groupby("direction"):
            dirs[int(d_)] = {"n": int(len(td)), "sum_net": float(td["net_return"].sum()), "mean_net": float(td["net_return"].mean()), "win": float((td["net_return"] > 0).mean())}
        out[mult] = {"years": years, "legs": legs, "dirs": dirs}
    return out


def show(df: pd.DataFrame, cols=None, sort="sharpe1", n=60) -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 90)
    cols = cols or ["name", "ret1", "sharpe1", "ret2", "sharpe2", "mdd1", "trades", "exposure", "win", "pf", "avg_bars", "costs1"]
    d = df.sort_values(sort, ascending=False)[cols].head(n)
    print(d.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
