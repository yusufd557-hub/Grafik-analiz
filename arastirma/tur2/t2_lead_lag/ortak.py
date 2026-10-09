"""t2_lead_lag tarama yardımcıları (yalnız dev_train; bütün ölçümler deftere yazılır).

- ``tara(configs, csv_path, mults)``: her yapılandırmayı ``evaluate(spec,
  windows=("dev_train",), cost_multipliers=mults)`` ile ölçer (defter kaydı
  açık). Defterde aynı ad + pencere + maliyet katıyla satırı olan yapılandırma
  yeniden çalıştırılmaz; sonucu defterden okunur (kesintiye dayanıklı).
- ``yillik(spec)``: eğitim içi yıllara göre tutarlılık. Veri önce
  31.12.2024'te kesilir, sonra sinyal ve backtest (harness fonksiyonları)
  çalışır; iç doğrulama verisi hiç yüklenmez. Yalnız defterde zaten ölçülmüş
  yapılandırmalar için kullanılır.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

assert os.environ.get("GRAFIK_ANALIZ_PROTOKOL") == "2", "GRAFIK_ANALIZ_PROTOKOL=2 gerekli"

import numpy as np
import pandas as pd

from grafik_analiz.research import ledger, protocol
from grafik_analiz.research.evaluate import backtest, compute_signals, evaluate, load_data
from grafik_analiz.research.metrics import daily_returns
from grafik_analiz.strategies.t2_lead_lag import FAMILY, make_spec

assert protocol.PROTOCOL_VERSION == "2"
KLASOR = Path(__file__).resolve().parent
END = protocol.DEV_TRAIN_END

ALANLAR = [
    "ad", "interval", "params", "maliyet", "total_return", "sharpe", "max_drawdown", "trades",
    "alfa", "beta", "alfa_t", "exposure", "total_costs", "total_funding", "avg_trade", "win_rate",
    "avg_bars", "sure_s",
]


def _defter() -> dict:
    df = ledger.trials(FAMILY)
    out = {}
    if df.empty:
        return out
    for _, row in df.iterrows():
        if row["pencere"] != "dev_train":
            continue
        out[(row["strateji"], float(row["maliyet_kat"]))] = row["olcu"]
    return out


def tara(configs, csv_path, mults=(1.0,), log=print):
    """configs: [(ad, interval, params)]"""
    csv_path = Path(csv_path)
    yeni = not csv_path.exists()
    seen = _defter()
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ALANLAR)
        if yeni:
            w.writeheader()
        for ad, iv, params in configs:
            spec = make_spec(ad, iv, **dict(params))
            todo = tuple(m for m in mults if (spec.name, float(m)) not in seen)
            if not todo:
                log(f"ATLA (defterde) {spec.name}")
                continue
            t0 = time.time()
            try:
                res = evaluate(spec, windows=("dev_train",), cost_multipliers=todo)
            except Exception as exc:  # pragma: no cover
                log(f"HATA {spec.name}: {exc!r}")
                continue
            dt = time.time() - t0
            for m in todo:
                r = res["dev_train"][m]
                row = {k: r.get(k) for k in ALANLAR if k in r}
                row.update(ad=spec.name, interval=iv, params=json.dumps(params, sort_keys=True), maliyet=m, sure_s=round(dt, 1))
                w.writerow(row)
                fh.flush()
                log(
                    f"{spec.name} x{m}: net={r.get('total_return', float('nan')):+.4f} sh={r.get('sharpe') or float('nan'):+.2f} "
                    f"dd={r.get('max_drawdown', float('nan')):+.3f} n={r.get('trades')} alfa={r.get('alfa') or float('nan'):+.4f} "
                    f"beta={r.get('beta') or float('nan'):+.3f} t={r.get('alfa_t') or float('nan'):+.2f} "
                    f"maliyet={r.get('total_costs', float('nan')):.3f} fon={r.get('total_funding', float('nan')):+.3f} ({dt:.0f}s)"
                )


def yillik(spec, mult=1.0) -> pd.Series:
    """Eğitim içi yıllık bileşik net getiri (veri 2025-01-01'de kesilerek)."""
    data, funding = load_data(spec, "dev")
    data = {leg: f[f["close_time"] < END] for leg, f in data.items()}
    funding = {s: f[f.index < END] for s, f in funding.items()}
    sig = compute_signals(spec, data, funding)
    r = backtest(spec, data, funding, sig, mult).returns
    d = daily_returns(r)
    return (1 + d).groupby(d.index.year).prod() - 1


def log_to(path):
    fh = open(path, "a", encoding="utf-8")

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        fh.write(line + "\n")
        fh.flush()

    return log
