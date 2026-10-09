"""Geniş vadeli evren: zamana bağlı, hayatta kalan yanlılığı olmadan.

Her ayın evreni, bir önceki ayın son 30 gününde en çok USDT işlem hacmi olan
`n` sözleşmedir. Bilgi yalnızca ay başında bilinen veriden gelir. Listeden
sonradan çıkarılan sözleşmeler de dahildir. Sabit değerli (stablecoin)
sözleşmeler dışarıda bırakılır.

    python -m grafik_analiz.research.universe indir      # günlük mumlar + evren + 4s mum ve fonlama
    python -m grafik_analiz.research.universe evren      # yalnız evren tablosunu yeniden hesapla
"""

from __future__ import annotations

import argparse
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from ..data import CandleStore
from ..data.binance import DataError, fetch_month_archive, fetch_month_funding
from ..data.extra import S3_LIST, futures_symbols
from .protocol import research_data_dir

STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "USTCUSDT", "EURUSDT", "USDEUSDT", "XUSDUSDT", "RLUSDUSDT", "BFUSDUSDT"}
TOP_N = 30
WORKERS = 16


def universe_path(root: Path | None = None) -> Path:
    return (root or research_data_dir()) / "vadeli" / "evren.parquet"


def _months_listed(session: requests.Session, symbol: str, interval: str, kind: str = "klines") -> list[str]:
    prefix = f"data/futures/um/monthly/{kind}/{symbol}/" + (f"{interval}/" if kind == "klines" else "")
    marker, months = "", []
    while True:
        r = session.get(S3_LIST, params={"prefix": prefix, "marker": marker}, timeout=60)
        r.raise_for_status()
        keys = re.findall(r"<Key>([^<]+\.zip)</Key>", r.text)
        months += [m for m in re.findall(r"-(\d{4}-\d{2})\.zip", " ".join(keys))]
        if "<IsTruncated>true</IsTruncated>" not in r.text or not keys:
            break
        marker = keys[-1]
    return sorted(set(months))


def _download_symbol(root: Path, symbol: str, interval: str, start: str, with_funding: bool) -> str:
    store = CandleStore(root, market="futures")
    session = requests.Session()
    path = store.path(symbol, interval)
    if path.exists():
        return "var"
    months = [m for m in _months_listed(session, symbol, interval) if m >= start]
    parts = []
    for m in months:
        y, mo = map(int, m.split("-"))
        for attempt in range(3):
            try:
                chunk = fetch_month_archive(session, symbol, interval, y, mo, market="futures")
                if chunk is not None and not chunk.empty:
                    parts.append(chunk)
                break
            except (requests.RequestException, DataError):
                time.sleep(2**attempt)
    if not parts:
        return "yok"
    frame = pd.concat(parts)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    store.save(symbol, interval, frame)
    if with_funding and not store.funding_path(symbol).exists():
        fparts = []
        for m in _months_listed(session, symbol, "", kind="fundingRate"):
            if m < start:
                continue
            y, mo = map(int, m.split("-"))
            for attempt in range(3):
                try:
                    f = fetch_month_funding(session, symbol, y, mo)
                    if f is not None and not f.empty:
                        fparts.append(f)
                    break
                except (requests.RequestException, DataError):
                    time.sleep(2**attempt)
        if fparts:
            fr = pd.concat(fparts)
            fr = fr[~fr.index.duplicated(keep="last")].sort_index()
            fpath = store.funding_path(symbol)
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fr.to_parquet(fpath)
    return f"{len(frame)} mum"


def download(root: Path, symbols: list[str], interval: str, start: str = "2020-01", with_funding: bool = False) -> dict:
    results: dict = {}
    lock = threading.Lock()
    done = [0]

    def one(sym):
        try:
            res = _download_symbol(root, sym, interval, start, with_funding)
        except Exception as exc:  # noqa: BLE001 — bir sembolün hatası diğerlerini durdurmamalı
            res = f"hata: {exc}"
        with lock:
            done[0] += 1
            if done[0] % 50 == 0:
                print(f"  {interval}: {done[0]}/{len(symbols)}", flush=True)
        return sym, res

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for sym, res in pool.map(one, symbols):
            results[sym] = res
    return results


def build_universe(root: Path, n: int = TOP_N) -> pd.DataFrame:
    """Ay başı → o ay işlem görecek ilk `n` sözleşme (önceki 30 günün hacmine göre)."""
    base = root / "vadeli"
    volumes = {}
    for path in sorted(base.glob("*/1d.parquet")):
        sym = path.parent.name
        if sym in STABLE:
            continue
        frame = pd.read_parquet(path, columns=["quote_volume", "close_time"])
        volumes[sym] = frame["quote_volume"]
    vol = pd.DataFrame(volumes).sort_index()
    rows = []
    months = pd.date_range(vol.index.min().normalize() + pd.offsets.MonthBegin(1), pd.Timestamp.now(tz="UTC"), freq="MS", tz="UTC")
    for month in months:
        window = vol[(vol.index >= month - pd.Timedelta(days=30)) & (vol.index < month)]
        if window.empty:
            continue
        # Pencerede en az 20 gün işlem görmüş olmalı (yeni listelenenlerin kısmi hacmi yanıltmasın).
        counts = window.notna().sum()
        total = window.sum()[counts >= 20].sort_values(ascending=False)
        for rank, sym in enumerate(total.index[:n], 1):
            rows.append({"ay": month, "sira": rank, "sembol": sym, "hacim_30g": float(total[sym])})
    table = pd.DataFrame(rows)
    table.to_parquet(universe_path(root))
    return table


def load_universe(root: Path | None = None) -> pd.DataFrame:
    return pd.read_parquet(universe_path(root))


def members_at(time: pd.Timestamp, root: Path | None = None, table: pd.DataFrame | None = None) -> list[str]:
    """Verilen anda geçerli evren (o ayın başında belirlenmiş liste)."""
    table = load_universe(root) if table is None else table
    month = pd.Timestamp(year=time.year, month=time.month, day=1, tz="UTC")
    return table.loc[table["ay"] == month, "sembol"].tolist()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("komut", choices=["indir", "evren"])
    parser.add_argument("--n", type=int, default=TOP_N)
    parser.add_argument("--veri", type=Path, default=None)
    args = parser.parse_args()
    root = args.veri or research_data_dir()
    if args.komut == "indir":
        symbols = [s for s in futures_symbols() if s not in STABLE]
        print(f"{len(symbols)} sözleşme için günlük mumlar", flush=True)
        download(root, symbols, "1d", start="2020-01")
    table = build_universe(root, args.n)
    members = sorted(table["sembol"].unique())
    print(f"evren: {table['ay'].nunique()} ay, {len(members)} farklı sözleşme", flush=True)
    if args.komut == "indir":
        print("evren üyeleri için 4 saatlik mumlar ve fonlama", flush=True)
        res = download(root, members, "4h", start="2020-01", with_funding=True)
        print({k: v for k, v in res.items() if not str(v).endswith("mum") and v != "var"}, flush=True)
    print("BITTI", flush=True)


if __name__ == "__main__":
    main()
