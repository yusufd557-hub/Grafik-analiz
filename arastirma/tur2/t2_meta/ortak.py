"""t2_meta arama yardımcıları (yalnız dev_train).

- ``tara(configs, csv)``: her yapılandırmayı ``evaluate(spec, windows=("dev_train",))``
  ile ölçer (deftere yazılır) ve özetini CSV'ye ekler.
- ``tani(params, interval)``: veriyi 2025-01-01 öncesine keserek olay sayısı,
  etiket taban oranı ve ileriye yürüyen AUC (yalnız dev_train olayları) verir.
  Defter dışı betimleyici ölçüdür; raporda açıklanır.

Ortam: GRAFIK_ANALIZ_PROTOKOL=2 zorunlu.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

assert os.environ.get("GRAFIK_ANALIZ_PROTOKOL") == "2", "GRAFIK_ANALIZ_PROTOKOL=2 gerekli"

from grafik_analiz.research.evaluate import evaluate, load_data  # noqa: E402
from grafik_analiz.research.protocol import DEV_TRAIN_END  # noqa: E402
from grafik_analiz.strategies import t2_meta as tm  # noqa: E402

KLASOR = Path(__file__).resolve().parent

KEEP = ["total_return", "cagr", "sharpe", "max_drawdown", "trades", "win_rate", "exposure", "alfa", "beta", "alfa_t", "p_value", "total_costs", "total_funding"]


def isim(interval: str, p: dict) -> str:
    q = {**tm.DEFAULTS, **p}
    parts = [tm.FAMILY, interval, q["birincil"].replace("+", "-")]
    if q.get("topluluk"):
        parts.append("top[" + q["topluluk"].replace("=", "").replace(",", "-").replace(";", "_") + "]")
    for kind in q["birincil"].split("+"):
        if kind == "kanal":
            parts.append(f"n{q['n']}")
        elif kind == "donus":
            parts.append(f"k{q['k']}z{q['z']}")
        elif kind == "fonlama":
            parts.append(f"fz{q['fz']}")
        elif kind == "ema":
            parts.append(f"e{q['hizli']}-{q['yavas']}")
    if q["cikis"] == "bariyer":
        parts.append(f"b{q['tp']}-{q['sl']}-H{q['H']}")
    else:
        parts.append(f"iz{q['iz_k']}-H{q['H']}")
    if q["yon"] != "iki":
        parts.append(q["yon"])
    parts.append(q["model"])
    if q["model"] != "hepsi":
        parts.append(q["ozellik"])
        parts.append(f"{q['kural']}{q['esik'] if q['kural'] == 'mutlak' else q['delta']}")
        if q["boyut"] != "ikili":
            parts.append(f"boy{q['boyut']}")
        extra = []
        for k in ("yeniden", "min_olay", "pencere_gun", "hgb_iter", "hgb_lr", "hgb_yaprak", "hgb_min_yaprak", "hgb_l2", "C", "agirlik"):
            if q[k] != tm.DEFAULTS[k]:
                extra.append(f"{k}{q[k]}")
        parts.extend(extra)
    return "_".join(str(x) for x in parts)


def tara(configs: list[tuple[str, dict]], csv: str, maliyetler=(1.0,)) -> pd.DataFrame:
    path = KLASOR / csv
    rows = []
    for interval, p in configs:
        name = isim(interval, p)
        spec = tm.make_spec(name, interval, **p)
        t0 = time.time()
        res = evaluate(spec, windows=("dev_train",), cost_multipliers=tuple(maliyetler))
        diag = tani_egitim(spec)
        for mult in maliyetler:
            m = res["dev_train"][mult]
            row = {"isim": name, "aralik": interval, "maliyet": mult, **{k: m.get(k) for k in KEEP}, **diag, "sure": round(time.time() - t0, 1), "params": json.dumps(p, sort_keys=True)}
            rows.append(row)
            print(
                f"{name} x{mult}: ret {m.get('total_return', float('nan')):+.3f} sh {m.get('sharpe', float('nan')):.2f} "
                f"dd {m.get('max_drawdown', float('nan')):.3f} tr {m.get('trades')} alfa {m.get('alfa', float('nan')):+.3f} "
                f"b {m.get('beta', float('nan')):+.2f} t {m.get('alfa_t', float('nan')):+.2f} | olay {diag['e_olay']} taban {diag['e_taban']:.3f} "
                f"auc {diag['e_auc']:.3f} kabul {diag['e_kabul']} k_net {diag['e_kabul_net']:+.4f} r_net {diag['e_red_net']:+.4f} ({time.time() - t0:.0f}s)",
                flush=True,
            )
        frame = pd.DataFrame(rows[-len(maliyetler):])
        frame.to_csv(path, mode="a", header=not path.exists(), index=False)
    return pd.DataFrame(rows)


def tani_egitim(spec) -> dict:
    """Aynı (önbellekteki) tahminlerden, yalnız etiketi 2025-01-01'den önce bilinen olaylarla tanı ölçüleri.

    Tahminler nedensel olduğundan bu olayların olasılıkları kesik veriyle aynıdır; dev_valid
    olaylarına ve etiketlerine bakılmaz. Toplulukta alt yapılandırmaların olayları birleştirilir.
    """
    q0 = {**tm.DEFAULTS, **spec.params}
    data, funding = load_data(spec, "dev")
    lim = DEV_TRAIN_END.value
    nets, prs, accs = [], [], []
    for q in tm.expand_ensemble(q0):
        ev = tm.predictions(data, funding, q)
        if ev.empty:
            continue
        ev = ev[(ev["_known"].to_numpy() < lim) & (ev["_ts"].to_numpy() < lim)]
        acc, _ = tm.decisions(ev, q)
        nets.append(ev["_net"].to_numpy(dtype=float))
        prs.append(ev["_p"].to_numpy(dtype=float))
        accs.append(acc)
    if not nets:
        return {"e_olay": 0, "e_taban": float("nan"), "e_auc": float("nan"), "e_kabul": 0, "e_kabul_net": float("nan"), "e_red_net": float("nan"), "e_tum_net": float("nan")}
    net, pr, acc = np.concatenate(nets), np.concatenate(prs), np.concatenate(accs)
    y = (net > 0).astype(int)
    m = np.isfinite(pr)
    acc &= m
    return {
        "e_olay": int(len(net)),
        "e_taban": float(y.mean()) if len(y) else float("nan"),
        "e_auc": auc(y[m], pr[m]) if q0["model"] != "hepsi" else float("nan"),
        "e_kabul": int(acc.sum()),
        "e_kabul_net": float(net[acc].mean()) if acc.any() else float("nan"),
        "e_red_net": float(net[m & ~acc].mean()) if (m & ~acc).any() else float("nan"),
        "e_tum_net": float(net[m].mean()) if m.any() else float("nan"),
    }


def egitim_verisi(interval: str):
    """2025-01-01 öncesine kesilmiş veri (defter dışı tanı için)."""
    spec = tm.make_spec("tani", interval)
    data, funding = load_data(spec, "dev")
    data = {leg: df[df.index + (df.index[1] - df.index[0]) <= DEV_TRAIN_END] for leg, df in data.items()}
    funding = {s: f[f.index < DEV_TRAIN_END] for s, f in funding.items()}
    return data, funding


def auc(y: np.ndarray, s: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score

    ok = np.isfinite(s)
    if ok.sum() < 20 or len(np.unique(y[ok])) < 2:
        return float("nan")
    return float(roc_auc_score(y[ok], s[ok]))


def tani(interval: str, p: dict, data=None, funding=None) -> dict:
    q = {**tm.DEFAULTS, **p}
    if data is None:
        data, funding = egitim_verisi(interval)
    ev = tm.predictions(data, funding, q)
    known = ev["_known"].to_numpy() < np.iinfo(np.int64).max
    net = ev["_net"].to_numpy(dtype=float)
    pr = ev["_p"].to_numpy(dtype=float)
    y = (net > 0).astype(int)
    m = known & np.isfinite(pr)
    acc, size = tm.decisions(ev, q)
    out = {
        "olay": int(len(ev)),
        "etiketli": int(known.sum()),
        "taban": float(y[known].mean()) if known.any() else float("nan"),
        "ort_net": float(np.nanmean(net[known])) if known.any() else float("nan"),
        "tahminli": int(m.sum()),
        "auc": auc(y[m], pr[m]) if q["model"] != "hepsi" else float("nan"),
        "tahminli_ort_net": float(np.nanmean(net[m])) if m.any() else float("nan"),
        "kabul": int((acc & m).sum()),
        "kabul_ort_net": float(np.nanmean(net[acc & m])) if (acc & m).any() else float("nan"),
        "red_ort_net": float(np.nanmean(net[~acc & m])) if (~acc & m).any() else float("nan"),
    }
    return out


if __name__ == "__main__":
    print(isim(sys.argv[1] if len(sys.argv) > 1 else "4h", {}))
