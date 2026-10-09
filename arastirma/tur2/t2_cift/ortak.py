"""t2_cift araştırma yardımcıları (yalnız protokol sürüm 2).

- `tara(konfig_listesi)`: her yapılandırma `evaluate(spec, windows=("dev_train",),
  cost_multipliers=(1.0, 2.0))` ile değerlendirilir (deftere yazılır).
- `egitim_dokumu(spec)`: veriyi 31.12.2024 sonunda (DEV_TRAIN_END öncesi) keserek
  eğitim içi yıllık getiri, maliyet ve fonlama dökümü. dev_valid verisi hiç
  hesaba girmez. Yalnız önceden deftere yazılmış yapılandırmalar için kullanılır.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import backtest, compute_signals, evaluate, load_data
from grafik_analiz.research.metrics import daily_returns
from grafik_analiz.strategies.t2_cift import make_spec

assert protocol.PROTOCOL_VERSION == "2", "GRAFIK_ANALIZ_PROTOKOL=2 gerekli"
TRAIN_END = protocol.DEV_TRAIN_END


def ad(interval: str, p: dict) -> str:
    parts = [interval, "-".join(p.get("ciftler", ["ETHBTC"])), p.get("hedge", "bir")]
    keys = ["z_tur", "k", "vol_win", "hedge_win", "z_win", "z_in", "z_exit", "z_stop", "max_bar", "rejim", "rejim_win", "rejim_esik", "teyit", "limit_bps", "limit_bar", "limit_mod"]
    for k in keys:
        if k in p and p[k] is not None and p[k] is not False:
            parts.append(f"{k}{p[k]}")
    return "_".join(str(x) for x in parts)


def degerlendir(interval: str, p: dict, mults=(1.0, 2.0)) -> dict:
    spec = make_spec(ad(interval, p), interval, **p)
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=mults)
    m1 = res["dev_train"][1.0]
    row = {
        "ad": spec.name,
        "interval": interval,
        **{k: (json.dumps(v) if isinstance(v, (list, tuple)) else v) for k, v in p.items()},
        "ret": m1.get("total_return"),
        "sharpe": m1.get("sharpe"),
        "mdd": m1.get("max_drawdown"),
        "trades": m1.get("trades"),
        "alfa": m1.get("alfa"),
        "beta": m1.get("beta"),
        "alfa_t": m1.get("alfa_t"),
        "maliyet": m1.get("total_costs"),
        "fonlama": m1.get("total_funding"),
        "maruz": m1.get("exposure"),
        "win": m1.get("win_rate"),
    }
    if 2.0 in res["dev_train"]:
        m2 = res["dev_train"][2.0]
        row["ret2"] = m2.get("total_return")
        row["sharpe2"] = m2.get("sharpe")
    return row


def tara(konfigler: list[tuple[str, dict]], cikti: str | None = None, mults=(1.0, 2.0)) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    for i, (iv, p) in enumerate(konfigler):
        rows.append(degerlendir(iv, p, mults))
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(konfigler)} {time.time() - t0:.0f}s", flush=True)
            if cikti:
                pd.DataFrame(rows).to_csv(cikti, index=False)
    df = pd.DataFrame(rows)
    if cikti:
        df.to_csv(cikti, index=False)
    return df


def _cut(data: dict, funding: dict) -> tuple[dict, dict]:
    d = {leg: f[f.index < TRAIN_END] for leg, f in data.items()}
    # Kesilmiş verideki son barın kapanışından sonraki fonlama kayıtları da atılır.
    fu = {s: f[f.index < TRAIN_END] for s, f in funding.items()}
    return d, fu


def egitim_dokumu(interval: str, p: dict) -> dict:
    """Eğitim dönemi içi döküm (veri DEV_TRAIN_END'de kesilir)."""
    spec = make_spec(ad(interval, p), interval, **p)
    data, funding = load_data(spec, "dev")
    data, funding = _cut(data, funding)
    sig = compute_signals(spec, data, funding)
    res = backtest(spec, data, funding, sig, 1.0)
    r = res.returns
    yearly = (1 + r).groupby(r.index.year).prod() - 1
    gross = pd.Series(0.0, index=r.index)
    w = spec.leg_weights()
    leg_info = {}
    for leg, lr in res.legs.items():
        gross = gross.add(w[leg] * lr.gross.reindex(r.index).fillna(0.0), fill_value=0.0)
        leg_info[leg[1]] = {
            "brut": float((w[leg] * lr.gross).sum()),
            "maliyet": float((w[leg] * lr.cost).sum()),
            "fonlama": float((w[leg] * lr.funding).sum()),
            "ort_poz": float(lr.position.mean()),
        }
    fy = res.funding.groupby(res.funding.index.year).sum()
    cy = res.costs.groupby(res.costs.index.year).sum()
    gy = gross.groupby(gross.index.year).sum()
    return {
        "yillik": yearly.round(4).to_dict(),
        "yillik_brut_toplam": gy.round(4).to_dict(),
        "yillik_maliyet": cy.round(4).to_dict(),
        "yillik_fonlama": fy.round(4).to_dict(),
        "bacak": leg_info,
        "fonlama_toplam": float(res.funding.sum()),
        "maliyet_toplam": float(res.costs.sum()),
        "brut_toplam": float(gross.sum()),
    }
