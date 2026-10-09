"""Dondurulan yapılandırmalar için `assert_causal` (performans hesaplamaz)."""

from __future__ import annotations

import json
from pathlib import Path

from grafik_analiz.research.evaluate import assert_causal
from grafik_analiz.research.protocol import PROTOCOL_VERSION
from grafik_analiz.strategies.t2_konumlanma import make_spec

HERE = Path(__file__).resolve().parent

if __name__ == "__main__":
    assert PROTOCOL_VERSION == "2"
    frozen = json.loads((HERE / "dondurma.json").read_text(encoding="utf-8"))["secilen"]
    for r in frozen:
        spec = make_spec(r["strateji"], r["evren"], r["dilim"], r["parametreler"])
        for fr in ((0.55, 0.8, 0.97), (0.3, 0.65, 0.9, 0.99)):
            assert_causal(spec, fractions=fr)
        print(f"geçti: {spec.name}", flush=True)
