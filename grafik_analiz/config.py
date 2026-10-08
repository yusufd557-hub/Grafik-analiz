"""Proje genelindeki sabitler: coinler, zaman dilimleri ve veri klasörü."""

from __future__ import annotations

import os
from pathlib import Path

SYMBOLS: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

INTERVALS: tuple[str, ...] = ("5m", "15m", "1h", "4h", "1d")

INTERVAL_MS: dict[str, int] = {
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}

INTERVAL_NAMES: dict[str, str] = {
    "5m": "5 dakika",
    "15m": "15 dakika",
    "1h": "1 saat",
    "4h": "4 saat",
    "1d": "Günlük",
}

# İlk indirmede ne kadar geriye gidileceği (YYYY-AA). Kısa zaman dilimlerinde
# bar sayısı hızla büyüdüğü için başlangıç daha yakındır. Coin bu tarihten
# sonra listelendiyse indirme listelendiği aydan başlar.
DEFAULT_HISTORY_START: dict[str, str] = {
    "5m": "2024-01",
    "15m": "2022-01",
    "1h": "2020-01",
    "4h": "2018-01",
    "1d": "2017-08",
}


def data_dir() -> Path:
    """Mum verisinin saklandığı klasör.

    `GRAFIK_ANALIZ_VERI` ortam değişkeniyle değiştirilebilir; varsayılan
    kullanıcı klasöründe `GrafikAnaliz/veri`.
    """
    override = os.environ.get("GRAFIK_ANALIZ_VERI")
    if override:
        return Path(override).expanduser()
    return Path.home() / "GrafikAnaliz" / "veri"


def validate_symbol(symbol: str) -> str:
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol = f"{symbol}USDT"
    return symbol


def validate_interval(interval: str) -> str:
    if interval not in INTERVAL_MS:
        raise ValueError(f"desteklenmeyen zaman dilimi: {interval} (geçerli: {', '.join(INTERVALS)})")
    return interval
