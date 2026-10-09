"""Ek vadeli piyasa verileri: konumlanma ölçüleri, prim endeksi ve sözleşme listesi.

- **Konumlanma (metrics):** Binance USDⓈ-M günlük arşivi, 5 dakikada bir:
  açık pozisyon (adet ve USDT), en büyük hesapların uzun/kısa oranı (hesap ve
  pozisyon bazında), bütün hesapların uzun/kısa oranı ve taker alım/satım
  hacim oranı. 2020-09'dan itibaren.
- **Prim endeksi:** vadeli fiyatın endeks fiyatına göre primi, mum biçiminde
  (aylık arşiv + REST).
- **Sözleşme listesi:** arşivdeki bütün USDⓈ-M sözleşmeleri, listeden
  çıkarılanlar dahil (hayatta kalan yanlılığını önlemek için).

Dosyalar: `veri/vadeli/<COIN>/konumlanma.parquet`, `veri/vadeli/<COIN>/prim_<dilim>.parquet`.
"""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from ..config import INTERVAL_MS
from .binance import DataError, RestClient, _download_verified, _read_csv_from_zip, parse_klines

BASE = "https://data.binance.vision/data/futures/um"
S3_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
WORKERS = 12
RETRIES = 3

METRIC_COLUMNS = {
    "sum_open_interest": "oi",
    "sum_open_interest_value": "oi_usdt",
    "count_toptrader_long_short_ratio": "top_hesap_oran",
    "sum_toptrader_long_short_ratio": "top_pozisyon_oran",
    "count_long_short_ratio": "genel_oran",
    "sum_taker_long_short_vol_ratio": "taker_oran",
}


def _base(root: Path, symbol: str) -> Path:
    return Path(root) / "vadeli" / symbol


def _parallel(fn, items, workers: int = WORKERS):
    local = threading.local()

    def session() -> requests.Session:
        if not hasattr(local, "s"):
            local.s = requests.Session()
        return local.s

    def run(item):
        for attempt in range(RETRIES):
            try:
                return fn(session(), item)
            except (requests.RequestException, DataError):
                if attempt + 1 == RETRIES:
                    return None
                time.sleep(2**attempt)
        return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, items))


def _save(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    frame.to_parquet(tmp)
    tmp.replace(path)


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(path)
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    return frame.sort_index()


# ---------------------------------------------------------------- konumlanma


def parse_metrics(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    if str(frame.iloc[0, 0]).strip() == "create_time":
        frame.columns = [str(c).strip() for c in frame.iloc[0]]
        frame = frame.iloc[1:]
    index = pd.DatetimeIndex(pd.to_datetime(frame["create_time"], utc=True), name="zaman")
    out = pd.DataFrame(
        {new: pd.to_numeric(frame[old], errors="coerce").to_numpy() for old, new in METRIC_COLUMNS.items() if old in frame},
        index=index,
    )
    return out[~out.index.duplicated(keep="last")].sort_index()


def metrics_path(root: Path, symbol: str) -> Path:
    return _base(root, symbol) / "konumlanma.parquet"


def load_metrics(root: Path, symbol: str) -> pd.DataFrame:
    return _load(metrics_path(root, symbol))


def update_metrics(root: Path, symbol: str, start: str = "2020-09-01", now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Günlük konumlanma arşivlerini (dün dahil) tamamlar.

    Her satırın zaman damgası ölçümün yapıldığı andır. Bir barda kullanılırken
    yalnızca zamanı barın kapanışından önce olan ölçümler kullanılmalıdır.
    """
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    existing = load_metrics(root, symbol)
    first = pd.Timestamp(start, tz="UTC") if existing.empty else existing.index[-1].floor("1D")
    days = pd.date_range(first, now.floor("1D") - pd.Timedelta(days=1), freq="1D", tz="UTC")

    def one(session, day):
        url = f"{BASE}/daily/metrics/{symbol}/{symbol}-metrics-{day:%Y-%m-%d}.zip"
        payload = _download_verified(session, url, True, 60.0)
        return None if payload is None else parse_metrics(_read_csv_from_zip(payload, url))

    chunks = [c for c in _parallel(one, list(days)) if c is not None and not c.empty]
    parts = ([existing] if not existing.empty else []) + chunks
    if not parts:
        raise DataError(f"{symbol} konumlanma verisi bulunamadı")
    frame = pd.concat(parts)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    _save(frame, metrics_path(root, symbol))
    return frame


# ---------------------------------------------------------------- prim endeksi


def premium_path(root: Path, symbol: str, interval: str) -> Path:
    return _base(root, symbol) / f"prim_{interval}.parquet"


def load_premium(root: Path, symbol: str, interval: str) -> pd.DataFrame:
    return _load(premium_path(root, symbol, interval))


def update_premium(
    root: Path,
    symbol: str,
    interval: str,
    start: str = "2020-01",
    now: pd.Timestamp | None = None,
    rest: RestClient | None = None,
) -> pd.DataFrame:
    """Prim endeksi mumları (açılış/yüksek/düşük/kapanış = prim oranı)."""
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    step = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
    existing = load_premium(root, symbol, interval)
    first = pd.Timestamp(start + "-01", tz="UTC") if existing.empty else existing.index[-1] + step
    month0 = pd.Timestamp(year=now.year, month=now.month, day=1, tz="UTC")
    months = list(pd.date_range(pd.Timestamp(year=first.year, month=first.month, day=1, tz="UTC"), month0 - pd.Timedelta(days=1), freq="MS"))

    def one(session, m):
        url = f"{BASE}/monthly/premiumIndexKlines/{symbol}/{interval}/{symbol}-{interval}-{m:%Y-%m}.zip"
        payload = _download_verified(session, url, True, 60.0)
        return None if payload is None else parse_klines(_read_csv_from_zip(payload, url))

    chunks = [c for c in _parallel(one, months) if c is not None and not c.empty]
    parts = ([existing] if not existing.empty else []) + chunks
    next_open = max([first] + [c.index[-1] + step for c in chunks])
    if next_open + step <= now:
        client = rest or RestClient(market="futures")
        rows: list = []
        cursor = int(next_open.value // 1_000_000)
        while True:
            batch = client._get(
                {"symbol": symbol, "interval": interval, "startTime": cursor, "limit": 1000},
                path="/fapi/v1/premiumIndexKlines",
            )
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < 1000:
                break
            cursor = int(batch[-1][0]) + int(step.total_seconds() * 1000)
        if rows:
            parts.append(parse_klines(rows))
    if not parts:
        raise DataError(f"{symbol} prim endeksi bulunamadı")
    frame = pd.concat(parts)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame[frame["close_time"] < now][["open", "high", "low", "close", "close_time"]]
    _save(frame, premium_path(root, symbol, interval))
    return frame


# ---------------------------------------------------------------- sözleşme listesi


def futures_symbols(session: requests.Session | None = None) -> list[str]:
    """Arşivdeki bütün USDⓈ-M USDT sürekli sözleşmeleri (listeden çıkanlar dahil)."""
    session = session or requests.Session()
    prefix = "data/futures/um/monthly/klines/"
    marker = ""
    found: list[str] = []
    while True:
        response = session.get(S3_LIST, params={"delimiter": "/", "prefix": prefix, "marker": marker}, timeout=60)
        response.raise_for_status()
        text = response.text
        found += re.findall(r"<Prefix>" + re.escape(prefix) + r"([^/<]+)/</Prefix>", text)
        if "<IsTruncated>true</IsTruncated>" not in text:
            break
        nxt = re.search(r"<NextMarker>([^<]+)</NextMarker>", text)
        if not nxt:
            break
        marker = nxt.group(1)
    # Yalnız USDT kotasyonlu sürekli sözleşmeler (çeyreklik vadeliler "_" içerir).
    return sorted({s for s in found if s.endswith("USDT") and "_" not in s})
