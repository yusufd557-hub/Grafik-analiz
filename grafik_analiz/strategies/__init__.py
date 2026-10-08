"""Araştırmadan çıkan aday stratejiler.

Her aile `grafik_analiz/strategies/<aile>.py` dosyasında `specs()` fonksiyonu
tanımlar; fonksiyon parametreleri dondurulmuş `StrategySpec` listesi döndürür.
`all_specs()` bütün ailelerin adaylarını toplar.
"""

from __future__ import annotations

import importlib
import pkgutil

from ..research.evaluate import StrategySpec


def all_specs() -> list[StrategySpec]:
    specs: list[StrategySpec] = []
    for module in pkgutil.iter_modules(__path__):
        if module.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{module.name}")
        if hasattr(mod, "specs"):
            specs.extend(mod.specs())
    return specs


def get(name: str) -> StrategySpec:
    for spec in all_specs():
        if spec.name == name:
            return spec
    raise KeyError(f"strateji bulunamadı: {name}")
