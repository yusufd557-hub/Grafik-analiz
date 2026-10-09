"""Dondurma: NOTLAR.md bölüm 4 ve 9'daki kuralın mekanik uygulanışı.

Yalnız eğitim (dev_train) ölçüleri kullanılır. Korelasyon için günlük
getiriler, mumlar ve fonlama 31.12.2024'te kesilerek yeniden hesaplanır
(iç doğrulama verisi hiç yüklenmez ya da kullanılmaz). Deftere yazmaz.

Çıktı: `dondurma.json`, ekrana seçim günlüğü.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import backtest, compute_signals, load_data
from grafik_analiz.research.metrics import daily_returns
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies.t2_konumlanma import make_spec

HERE = Path(__file__).resolve().parent
DEFAULTS = {"yon": "iki", "trend_gun": 0, "filtre": "yok", "gecikme_dk": 10, "emir": "piyasa", "limit_bar": 1}
KIND_GROUP = {"kalabalik_top": "kalabalik"}
CONTROL_KINDS = {"fiyat"}
MAX_PER_KIND = 2
MAX_FROZEN = 5
MAX_CORR = 0.70


def full_params(p: dict) -> dict:
    return {**DEFAULTS, **p}


def train_daily(universe: str, interval: str, params: dict) -> pd.Series:
    spec = make_spec("dondurma_kontrol", universe, interval, params)
    data, funding = load_data(spec)
    data = {leg: f[f["close_time"] < DEV_TRAIN_END] for leg, f in data.items()}
    funding = {s: f[f.index < DEV_TRAIN_END] for s, f in funding.items()}
    res = backtest(spec, data, funding, compute_signals(spec, data, funding), 1.0)
    return daily_returns(res.returns)


def main() -> None:
    assert PROTOCOL_VERSION == "2"
    rows = [json.loads(l) for l in (HERE / "egitim_sonuclari.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"toplam yapılandırma: {len(rows)}")
    for r in rows:
        r["fp"] = full_params(r["parametreler"])

    def neighbours(r):
        out = []
        for q in rows:
            if q is r or q["dilim"] != r["dilim"] or q["evren"] != r["evren"] or q["fp"]["kind"] != r["fp"]["kind"]:
                continue
            keys = set(q["fp"]) | set(r["fp"])
            diff = [k for k in keys if q["fp"].get(k) != r["fp"].get(k)]
            if len(diff) == 1:
                out.append(q)
        return out

    eligible = []
    for r in rows:
        e1, e2 = r["egitim_1x"], r["egitim_2x"]
        kind = r["fp"]["kind"]
        if kind in CONTROL_KINDS:
            continue
        ok = (
            (e2["total_return"] or -1) > 0
            and (e1["alfa"] or -1) > 0
            and (e1["alfa_t"] or -9) >= 1.5
            and (e1["trades"] or 0) >= 60
            and (e1["sharpe"] or -9) >= 0.5
        )
        if not ok:
            continue
        nb = neighbours(r)
        pos = sum(1 for q in nb if (q["egitim_1x"]["alfa"] or -1) > 0)
        r["komsu"] = (len(nb), pos)
        if len(nb) >= 2 and pos > len(nb) / 2:
            eligible.append(r)
    print(f"uygun ve sağlam: {len(eligible)}")
    eligible.sort(key=lambda r: -r["egitim_1x"]["alfa_t"])

    selected: list = []
    series: dict = {}
    per_kind: dict = {}
    log = []
    for r in eligible:
        if len(selected) >= MAX_FROZEN:
            break
        group = KIND_GROUP.get(r["fp"]["kind"], r["fp"]["kind"])
        name = r["strateji"]
        if per_kind.get(group, 0) >= MAX_PER_KIND:
            continue
        d = train_daily(r["evren"], r["dilim"], r["parametreler"])
        total = float((1 + d).prod() - 1)
        corrs = {s: float(pd.concat([d, series[s]], axis=1).dropna().corr().iloc[0, 1]) for s in series}
        worst = max(corrs.values()) if corrs else float("nan")
        msg = (
            f"{name}: alfa t {r['egitim_1x']['alfa_t']:.2f}, komşu {r['komsu'][1]}/{r['komsu'][0]} pozitif, "
            f"kesik veriyle eğitim getirisi {total:+.3f} (defter {r['egitim_1x']['total_return']:+.3f}), "
            f"en yüksek korelasyon {worst:.3f}"
        )
        if corrs and worst >= MAX_CORR:
            log.append("ret  " + msg)
            print("ret  " + msg, flush=True)
            continue
        log.append("SEÇ  " + msg)
        print("SEÇ  " + msg, flush=True)
        selected.append(r)
        series[name] = d
        per_kind[group] = per_kind.get(group, 0) + 1

    names = [r["strateji"] for r in selected]
    corr = pd.concat([series[n].rename(n) for n in names], axis=1).corr()
    print(corr.round(3).to_string())
    out = {
        "secilen": [
            {"strateji": r["strateji"], "evren": r["evren"], "dilim": r["dilim"], "parametreler": r["parametreler"], "egitim_1x": r["egitim_1x"], "egitim_2x": r["egitim_2x"], "komsu": r["komsu"]}
            for r in selected
        ],
        "korelasyon": corr.round(4).to_dict(),
        "gunluk": log,
        "uygun_sayisi": len(eligible),
        "toplam": len(rows),
    }
    (HERE / "dondurma.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
