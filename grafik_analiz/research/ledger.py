"""Deney defteri: değerlendirilen her strateji yapılandırması kayda geçer.

Kaç yapılandırma denendiğini bilmek, en iyi sonucun şansla bulunup
bulunmadığını ölçmek (Deflated Sharpe) için gerekir. Her aile kendi
dosyasına yazar: `arastirma/deneyler/<aile>.jsonl`.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .protocol import PROTOCOL_VERSION, research_dir


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if not math.isfinite(f) else round(f, 6)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (pd.Timestamp,)):
        return str(value)
    return value


def ledger_path(family: str, root: Path | None = None) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in family)
    return (root or research_dir()) / "deneyler" / f"{safe}.jsonl"


KEEP = ("total_return", "sharpe", "max_drawdown", "trades", "days", "p_value")


def record(
    family: str,
    name: str,
    params: dict,
    window: str,
    cost_multiplier: float,
    metrics: dict,
    root: Path | None = None,
) -> None:
    path = ledger_path(family, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protokol": PROTOCOL_VERSION,
        "aile": family,
        "strateji": name,
        "parametreler": _clean(params),
        "pencere": window,
        "maliyet_kat": cost_multiplier,
        "olcu": _clean({k: metrics.get(k) for k in KEEP}),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def trials(family: str | None = None, root: Path | None = None) -> pd.DataFrame:
    base = (root or research_dir()) / "deneyler"
    files = [ledger_path(family, root)] if family else sorted(base.glob("*.jsonl"))
    rows = []
    for f in files:
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)
