"""Dönem kilitli veri erişimi.

Geliştirme sırasında yalnızca `DEV_END` öncesi veri yüklenebilir. Görülmemiş
döneme (holdout) erişim `unlock_holdout()` çağrısı gerektirir; her açılış
gerekçesiyle `arastirma/holdout_kayit.jsonl` dosyasına yazılır. Böylece
holdout'a kaç kez ve neden bakıldığı denetlenebilir.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..data import FUTURES, SPOT, CandleStore
from .protocol import DEV_END, HOLDOUT_END, research_data_dir, research_dir


class HoldoutLocked(PermissionError):
    """Görülmemiş döneme izinsiz erişim."""


_UNLOCKED = False


def unlock_holdout(reason: str, ledger: Path | None = None) -> None:
    """Holdout erişimini açar ve gerekçeyi kayda geçirir."""
    global _UNLOCKED
    if not reason or len(reason.strip()) < 10:
        raise ValueError("holdout açılışı için açık bir gerekçe yazılmalı")
    path = ledger or (research_dir() / "holdout_kayit.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "gerekce": reason.strip()}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _UNLOCKED = True


def lock_holdout() -> None:
    global _UNLOCKED
    _UNLOCKED = False


def holdout_unlocked() -> bool:
    return _UNLOCKED


def _limit(scope: str) -> pd.Timestamp:
    if scope == "dev":
        return DEV_END
    if scope in ("holdout", "all"):
        if not _UNLOCKED:
            raise HoldoutLocked(
                "görülmemiş dönem kilitli: geliştirme sırasında yalnızca scope='dev' kullanılır"
            )
        return HOLDOUT_END if scope == "holdout" else pd.Timestamp.max.tz_localize("UTC")
    raise ValueError(f"bilinmeyen kapsam: {scope}")


@lru_cache(maxsize=64)
def _raw(market: str, symbol: str, interval: str, root: str) -> pd.DataFrame:
    return CandleStore(Path(root), market=market).load(symbol, interval)


@lru_cache(maxsize=16)
def _raw_funding(symbol: str, root: str) -> pd.DataFrame:
    return CandleStore(Path(root), market=FUTURES).load_funding(symbol)


def load(
    symbol: str,
    interval: str,
    market: str = SPOT,
    scope: str = "dev",
    root: Path | None = None,
) -> pd.DataFrame:
    """Kapsamın sonuna kadar (hariç) kapanmış mumlar.

    `scope="dev"`: geliştirme dönemi (DEV_END öncesi). `scope="holdout"`:
    HOLDOUT_END'e kadar bütün veri (ısınma için geliştirme dönemi dahil).
    `scope="all"`: eldeki bütün veri (ileriye dönük takip).
    """
    end = _limit(scope)
    frame = _raw(market, symbol, interval, str(root or research_data_dir()))
    if frame.empty:
        raise FileNotFoundError(f"araştırma verisi yok: {market} {symbol} {interval}")
    # Mumun kendisi sınırdan önce kapanmış olmalı.
    return frame[frame["close_time"] < end].copy()


def load_funding(symbol: str, scope: str = "dev", root: Path | None = None) -> pd.DataFrame:
    end = _limit(scope)
    frame = _raw_funding(symbol, str(root or research_data_dir()))
    return frame[frame.index < end].copy()


def clear_cache() -> None:
    _raw.cache_clear()
    _raw_funding.cache_clear()
