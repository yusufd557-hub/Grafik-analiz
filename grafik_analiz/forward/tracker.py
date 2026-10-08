"""İleriye dönük sanal takip: önce kaydet, sonra puanla.

Her çalıştırmada:

1. Takip edilen stratejilerin bacakları için veri güncellenir (yalnız kapanmış
   mumlar).
2. Strateji, kodu değiştirilmeden sinyal üretir. Henüz kaydedilmemiş her
   kapanmış bar için hedef pozisyon, **kayıt zamanı** ve **kod özeti** ile
   `ileri_takip/<strateji>.jsonl` dosyasına eklenir.
3. Puanlama yalnızca bu kayıtları kullanır. Bir barın hedefi, bir sonraki
   barın açılışında uygulanır (araştırmadaki işlem simülasyonuyla aynı
   kurallar ve maliyetler).

Bir kayıt, ait olduğu barın kapanışından sonraki bir bar süresi içinde
yapıldıysa "zamanında" sayılır. Zamanında yapılmamış kayıtların hedefi
puanlamada kullanılmaz; o barlarda bir önceki zamanında hedef korunur. İlk
çalıştırmadan önceki barlar kaydedilmez. Takip, ilk kaydın yapıldığı bardan
başlar.

Kod özeti değişirse (strateji veya simülasyon kodu değiştiyse) yeni kayıtlar
farklı sürüm olarak işaretlenir. Puanlama yalnızca ilk kaydın sürümüyle
yapılır; değişiklik raporda ayrıca belirtilir.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import INTERVAL_MS
from ..data import FUTURES, CandleStore
from ..research.evaluate import StrategySpec, backtest
from ..research.metrics import summarize
from ..strategies import get

REPO = Path(__file__).resolve().parents[2]
RECORD_DIR = REPO / "ileri_takip"
HISTORY_START = "2023-01"
"""Sinyallerin ısınması için indirilen geçmişin başlangıcı."""


@dataclass(frozen=True)
class Tracked:
    name: str
    note: str


TRACKED: tuple[Tracked, ...] = (
    Tracked(
        "kirilim_kanal4h_vadeli_uzun",
        "Protokol 1 finalisti; görülmemiş dönemde Seviye 1'i geçemedi. Bilgi amaçlı takip.",
    ),
    Tracked("fonlama_carry_sepet3_hizli", "Fonlama/carry; aday şartlarından işlem sayısını geçemedi. Bilgi amaçlı takip."),
    Tracked("fonlama_carry_sepet3_yavas_dusuk", "Fonlama/carry; aday şartlarından işlem sayısını geçemedi. Bilgi amaçlı takip."),
    Tracked("fonlama_carry_btc_surekli", "Fonlama/carry; aday şartlarından işlem sayısını geçemedi. Bilgi amaçlı takip."),
)


def default_data_dir() -> Path:
    return Path.home() / "GrafikAnaliz" / "ileri_veri"


def _leg_key(leg: tuple[str, str]) -> str:
    return f"{leg[0]}:{leg[1]}"


def code_hash(spec: StrategySpec) -> str:
    """Stratejinin modülü ve simülasyon/gösterge kodunun özeti."""
    modules = [
        inspect.getmodule(spec.signal_fn),
        importlib.import_module("grafik_analiz.research.backtest"),
        importlib.import_module("grafik_analiz.research.evaluate"),
        importlib.import_module("grafik_analiz.research.protocol"),
        importlib.import_module("grafik_analiz.indicators"),
    ]
    digest = hashlib.sha256()
    for mod in modules:
        if mod is not None and getattr(mod, "__file__", None):
            digest.update(Path(mod.__file__).read_bytes())
    digest.update(json.dumps(spec.params, sort_keys=True, default=str).encode())
    return digest.hexdigest()[:16]


def load_market_data(spec: StrategySpec, root: Path, now: pd.Timestamp, update: bool = True) -> tuple[dict, dict]:
    data: dict = {}
    funding: dict = {}
    for market, symbol in spec.legs:
        store = CandleStore(root, market=market)
        frame = store.update(symbol, spec.interval, start=HISTORY_START, now=now) if update else store.load(symbol, spec.interval)
        data[(market, symbol)] = frame
        if market == FUTURES and symbol not in funding:
            funding[symbol] = store.update_funding(symbol, start=HISTORY_START, now=now) if update else store.load_funding(symbol)
    return data, funding


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def record(
    spec: StrategySpec,
    root: Path,
    now: pd.Timestamp | None = None,
    out_dir: Path = RECORD_DIR,
    update: bool = True,
) -> list[dict]:
    """Yeni kapanmış barların hedef pozisyonlarını kaydeder; eklenen kayıtları döndürür."""
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    data, funding = load_market_data(spec, root, now, update=update)
    signals = spec.signal_fn(data, funding, **spec.params)

    step = pd.Timedelta(milliseconds=INTERVAL_MS[spec.interval])
    # Bütün bacaklarda kapanmış ortak son bar.
    last_common = min(frame.index[-1] for frame in data.values())
    path = out_dir / f"{spec.name}.jsonl"
    existing = _read(path)
    if existing:
        first_bar = pd.Timestamp(existing[-1]["bar"]) + step
    else:
        first_bar = last_common  # ilk çalıştırma: yalnız son kapanmış bar

    bars = pd.date_range(first_bar, last_common, freq=step, tz="UTC") if first_bar <= last_common else []
    version = code_hash(spec)
    added = []
    for bar in bars:
        close_time = bar + step
        targets = {}
        for leg in spec.legs:
            s = pd.Series(signals[leg], dtype=float)
            v = s.get(bar, np.nan)
            targets[_leg_key(leg)] = None if pd.isna(v) else float(v)
        entry = {
            "strateji": spec.name,
            "bar": bar.isoformat(),
            "kapanis": close_time.isoformat(),
            "kayit": now.isoformat(timespec="seconds"),
            "zamaninda": bool(now <= close_time + step),
            "kod": version,
            "hedef": targets,
        }
        added.append(entry)
    if added:
        out_dir.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for entry in added:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return added


def score(spec: StrategySpec, root: Path, out_dir: Path = RECORD_DIR, update: bool = False, now: pd.Timestamp | None = None) -> dict:
    """Kaydedilmiş hedeflerle sanal sonuç (yalnız ilk kayıt sürümü, yalnız zamanında kayıtlar)."""
    records = _read(out_dir / f"{spec.name}.jsonl")
    if not records:
        return {"kayit": 0}
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    data, funding = load_market_data(spec, root, now, update=update)
    version = records[0]["kod"]
    usable = [r for r in records if r["kod"] == version and r["zamaninda"]]
    start = pd.Timestamp(records[0]["bar"])

    signals = {}
    for leg in spec.legs:
        frame = data[leg]
        target = pd.Series(np.nan, index=frame.index)
        for r in usable:
            bar = pd.Timestamp(r["bar"])
            v = r["hedef"].get(_leg_key(leg))
            if bar in target.index and v is not None:
                target.loc[bar] = v
        # Kayıt öncesi: pozisyon yok. Zamanında kaydı olmayan barlarda önceki hedef korunur.
        target[target.index < start] = 0.0
        signals[leg] = target.ffill().fillna(0.0)

    result = backtest(spec, data, funding, signals, 1.0)
    stress = backtest(spec, data, funding, signals, 2.0)
    # Sonuç, ilk kaydın uygulandığı bardan (kayıt barı + 1) itibaren ölçülür.
    step = pd.Timedelta(milliseconds=INTERVAL_MS[spec.interval])
    eval_start = start + step
    m1 = summarize(result.returns, result.trades, result.exposure, result.costs, result.funding, eval_start, None)
    m2 = summarize(stress.returns, stress.trades, stress.exposure, stress.costs, stress.funding, eval_start, None)
    current = {k: v for k, v in records[-1]["hedef"].items()}
    return {
        "kayit": len(records),
        "zamaninda": sum(1 for r in records if r["zamaninda"]),
        "surum_degisti": any(r["kod"] != version for r in records),
        "ilk_bar": records[0]["bar"],
        "son_bar": records[-1]["bar"],
        "son_hedef": current,
        "olcu_1x": m1,
        "olcu_2x": m2,
    }


def _pct(x) -> str:
    if x is None or not np.isfinite(x):
        return "–"
    return f"%{100 * x:+.2f}".replace(".", ",")


def _leg_text(key: str, value: float) -> str:
    market, symbol = key.split(":")
    label = "spot" if market == "spot" else "vadeli"
    value = 0.0 if abs(value) < 1e-12 else value
    return f"{label} {symbol.replace('USDT', '')} {value:+.2f}".replace(".", ",")


def write_report(results: dict, out_dir: Path = RECORD_DIR, now: pd.Timestamp | None = None) -> Path:
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    notes = {t.name: t.note for t in TRACKED}
    lines = [
        "# İleriye Dönük Sanal Takip",
        "",
        f"Son güncelleme: {now:%Y-%m-%d %H:%M} UTC. Kurallar: `grafik_analiz/forward/tracker.py`.",
        "Sinyaller her 4 saatlik mum kapanınca **önce** kaydedilir; sonuç sonraki mumlarla hesaplanır.",
        "Maliyetler araştırma protokolüyle aynıdır (spot %0,12, vadeli %0,07 taraf başına; fonlama dahil).",
        "",
        "| Strateji | Takip başlangıcı | Kayıt (zamanında) | Net (1×) | Net (2×) | En büyük düşüş | İşlem | Son hedef |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, r in results.items():
        if not r.get("kayit"):
            lines.append(f"| `{name}` | – | 0 | – | – | – | – | – |")
            continue
        m1, m2 = r["olcu_1x"], r["olcu_2x"]
        hedef = ", ".join(_leg_text(k, v) for k, v in r["son_hedef"].items() if v is not None)
        lines.append(
            f"| `{name}` | {r['ilk_bar'][:16].replace('T', ' ')} | {r['kayit']} ({r['zamaninda']}) | "
            f"{_pct(m1.get('total_return'))} | {_pct(m2.get('total_return'))} | {_pct(m1.get('max_drawdown'))} | "
            f"{m1.get('trades', 0)} | {hedef} |"
        )
    lines += ["", "## Notlar", ""]
    for name in results:
        lines.append(f"- `{name}`: {notes.get(name, '')}" + (" **Kod sürümü değişti.**" if results[name].get("surum_degisti") else ""))
    lines += [
        "",
        "Protokole göre bir değerlendirme en az 90 gün ve 30 işlem sonra yapılır; daha kısa sürelerdeki sonuçlar",
        "yalnız durum bilgisidir.",
        "",
    ]
    path = out_dir / "RAPOR.md"
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run(root: Path | None = None, out_dir: Path = RECORD_DIR, now: pd.Timestamp | None = None) -> dict:
    root = root or default_data_dir()
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    results = {}
    for item in TRACKED:
        spec = get(item.name)
        added = record(spec, root, now=now, out_dir=out_dir)
        results[item.name] = score(spec, root, out_dir=out_dir, now=now)
        print(f"{item.name}: {len(added)} yeni kayıt, toplam {results[item.name].get('kayit', 0)}", flush=True)
    write_report(results, out_dir, now)
    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="İleriye dönük sanal takip: kaydet ve puanla")
    parser.add_argument("--veri", type=Path, default=None, help="veri klasörü (varsayılan ~/GrafikAnaliz/ileri_veri)")
    args = parser.parse_args()
    run(args.veri)


if __name__ == "__main__":
    main()
