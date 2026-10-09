"""t2_konumlanma: eğitim dönemi (dev_train) taraması.

Her yapılandırma `evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))`
ile ölçülür (deney defterine yazılır). Özet satırları `egitim_sonuclari.jsonl`
dosyasına eklenir. İç doğrulama (dev_valid) bu betikte hiç hesaplanmaz.

Kullanım (protokol 2 ortamıyla):
    python arastirma/tur2/t2_konumlanma/tara.py <asama>
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

from grafik_analiz.research.evaluate import evaluate
from grafik_analiz.research.protocol import PROTOCOL_VERSION
from grafik_analiz.strategies.t2_konumlanma import make_spec

OUT = Path(__file__).resolve().parent / "egitim_sonuclari.jsonl"

SHORT = {
    "kind": "",
    "mod": "",
    "oran": "",
    "yon": "y",
    "k": "k",
    "w_gun": "w",
    "a": "a",
    "b": "b",
    "tut": "t",
    "n": "n",
    "c": "c",
    "cx": "cx",
    "isaret": "s",
    "trend_gun": "tr",
    "filtre": "",
}


def name_for(universe: str, interval: str, params: dict) -> str:
    parts = [params["kind"], interval, universe]
    for key, value in params.items():
        if key == "kind":
            continue
        if key == "filtre" and value == "yok":
            continue
        if key == "yon" and value == "iki":
            continue
        parts.append(f"{SHORT.get(key, key)}{value}")
    return "t2_konumlanma_" + "_".join(str(p) for p in parts)


def grid(**axes):
    keys = list(axes)
    for values in itertools.product(*(axes[k] for k in keys)):
        yield dict(zip(keys, values))


def stage1():
    """Geniş ilk tarama: her fikrin kaba bir ızgarası, üç coinlik sepet."""
    cfgs = []
    for iv, ks, tuts in (("1h", (4, 12, 24), (12, 48)), ("4h", (1, 3, 6), (3, 12))):
        for p in grid(kind=["oi"], mod=["tasfiye", "birikim"], k=ks, w_gun=[30], a=[1.0], b=[1.5, 2.5], tut=tuts):
            cfgs.append(("SEPET3", iv, p))
    for iv in ("1h", "4h"):
        for p in grid(kind=["kalabalik"], oran=["genel"], w_gun=[7, 30, 90], c=[1.0, 2.0], cx=[0.0], isaret=[-1]):
            cfgs.append(("SEPET3", iv, p))
    for iv, ns in (("1h", (8, 24)), ("4h", (2, 6))):
        for p in grid(kind=["prim"], n=ns, w_gun=[7, 30, 90], c=[1.0, 2.0], cx=[0.0], isaret=[-1]):
            cfgs.append(("SEPET3", iv, p))
    for iv, ks in (("1h", (6, 24)), ("4h", (1, 6))):
        for p in grid(kind=["taker"], k=ks, w_gun=[30], c=[1.0, 2.0], cx=[0.0], isaret=[1, -1]):
            cfgs.append(("SEPET3", iv, p))
    for iv in ("1h", "4h"):
        for p in grid(kind=["fark"], w_gun=[7, 30], c=[1.0, 2.0], cx=[0.0], isaret=[1]):
            cfgs.append(("SEPET3", iv, p))
    return cfgs


STAGES = {"1": stage1}


def summary(name, universe, interval, params, res, seconds):
    t1 = res["dev_train"][1.0]
    t2 = res["dev_train"][2.0]
    keep = ("total_return", "sharpe", "max_drawdown", "trades", "alfa", "beta", "alfa_t", "exposure", "win_rate", "total_without_best", "total_funding", "total_costs")
    return {
        "strateji": name,
        "evren": universe,
        "dilim": interval,
        "parametreler": params,
        "egitim_1x": {k: t1.get(k) for k in keep},
        "egitim_2x": {k: t2.get(k) for k in ("total_return", "sharpe", "alfa", "alfa_t")},
        "sure_sn": round(seconds, 1),
    }


def main(stage: str) -> None:
    assert PROTOCOL_VERSION == "2", "GRAFIK_ANALIZ_PROTOKOL=2 olmalı"
    cfgs = STAGES[stage]()
    done = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["strateji"])
    print(f"aşama {stage}: {len(cfgs)} yapılandırma ({len(done)} daha önce)", flush=True)
    for i, (universe, interval, params) in enumerate(cfgs):
        name = name_for(universe, interval, params)
        if name in done:
            continue
        t = time.time()
        spec = make_spec(name, universe, interval, params)
        res = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))
        row = summary(name, universe, interval, params, res, time.time() - t)
        row["asama"] = stage
        with OUT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, default=float) + "\n")
        done.add(name)
        e = row["egitim_1x"]
        print(
            f"[{i + 1}/{len(cfgs)}] {name}: ret {e['total_return']:+.3f} sh {e['sharpe']:.2f} "
            f"alfa {e['alfa']:+.3f} t {e['alfa_t']:.2f} beta {e['beta']:+.2f} n {e['trades']} "
            f"2x {row['egitim_2x']['total_return']:+.3f} ({row['sure_sn']}s)",
            flush=True,
        )


if __name__ == "__main__":
    main(sys.argv[1])
