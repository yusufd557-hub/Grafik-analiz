"""Ön kayıtlı araştırma protokolü: dönemler, maliyetler ve geçme şartları.

Bu dosyadaki değerler strateji sonuçlarından **önce** belirlenmiştir
(bkz. `docs/PROTOKOL.md`). Sonuçlara bakarak değiştirilmez; değişirse yeni
bir protokol sürümü olarak kaydedilir ve eski sonuçlar ayrı tutulur.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROTOCOL_VERSION = "1"

# ---------------------------------------------------------------- dönemler

DEV_TRAIN_END = pd.Timestamp("2024-01-01", tz="UTC")
"""Parametreler yalnızca bu tarihten önceki veriyle seçilir."""

DEV_END = pd.Timestamp("2025-07-01", tz="UTC")
"""Geliştirme döneminin sonu (hariç). [DEV_TRAIN_END, DEV_END) iç doğrulamadır."""

HOLDOUT_START = DEV_END
HOLDOUT_END = pd.Timestamp("2026-10-01", tz="UTC")
"""Görülmemiş dönem: 1 Temmuz 2025 – 30 Eylül 2026. Finalistler burada tek kez ölçülür."""

FORWARD_START = HOLDOUT_END
"""İleriye dönük sanal takip bu tarihten sonraki, önceden kaydedilen sinyallerle yapılır."""

PERIODS: dict[str, tuple[pd.Timestamp | None, pd.Timestamp]] = {
    "dev": (None, DEV_END),
    "dev_train": (None, DEV_TRAIN_END),
    "dev_valid": (DEV_TRAIN_END, DEV_END),
    "holdout": (HOLDOUT_START, HOLDOUT_END),
}

# ---------------------------------------------------------------- maliyetler


@dataclass(frozen=True)
class Costs:
    fee: float
    """Taraf başına komisyon (oran). 0.001 = %0,1."""
    slippage: float
    """Taraf başına kayma (oran)."""

    @property
    def per_side(self) -> float:
        return self.fee + self.slippage

    def scaled(self, multiplier: float) -> Costs:
        return Costs(self.fee * multiplier, self.slippage * multiplier)


SPOT_COSTS = Costs(fee=0.0010, slippage=0.0002)
"""Binance spot standart: %0,1 komisyon (piyasa emri) + 2 bps kayma, taraf başına."""

FUTURES_COSTS = Costs(fee=0.0005, slippage=0.0002)
"""Binance USDⓈ-M standart: %0,05 taker komisyon + 2 bps kayma, taraf başına. Fonlama ayrıca."""

STRESS_MULTIPLIER = 2.0
"""Dayanıklılık testi: komisyon ve kayma iki katı."""

COSTS = {"spot": SPOT_COSTS, "futures": FUTURES_COSTS}

MAX_LEVERAGE = {"spot": 1.0, "futures": 1.0}
"""Araştırmada kaldıraç yok: bacak başına pozisyon büyüklüğü sermayenin en fazla 1 katı."""

# ---------------------------------------------------------------- geçme şartları

MIN_TRADES_VALID = 20
MIN_SHARPE_VALID = 0.5
MIN_TRADES_HOLDOUT = 20
MAX_FINALISTS = 3
HOLDOUT_CONFIDENCE = 0.95
"""Seviye 2: günlük net getiri ortalamasının tek yönlü alt sınırı bu güvenle (finalist
sayısına göre Bonferroni düzeltmeli) sıfırın üstünde olmalı."""
BOOTSTRAP_BLOCK_DAYS = 10
BOOTSTRAP_SAMPLES = 5000

# ---------------------------------------------------------------- yollar


def research_data_dir() -> Path:
    """Araştırma verisi (spot + vadeli + fonlama). `GRAFIK_ANALIZ_ARASTIRMA` ile değiştirilebilir."""
    override = os.environ.get("GRAFIK_ANALIZ_ARASTIRMA")
    if override:
        return Path(override).expanduser()
    return Path.home() / "GrafikAnaliz" / "arastirma_veri"


def research_dir() -> Path:
    """Deney defteri ve raporların tutulduğu depo klasörü (`arastirma/`)."""
    return Path(__file__).resolve().parents[2] / "arastirma"


BARS_PER_YEAR = {
    "5m": 365 * 24 * 12,
    "15m": 365 * 24 * 4,
    "1h": 365 * 24,
    "4h": 365 * 6,
    "1d": 365,
}
