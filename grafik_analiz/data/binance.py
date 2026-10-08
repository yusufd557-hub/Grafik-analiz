"""Binance spot mum verisi: aylık resmî arşiv ve REST API.

Geçmiş veri `data.binance.vision` aylık ZIP arşivlerinden alınır ve yayımlanan
SHA256 değeriyle doğrulanır. Arşivde henüz bulunmayan son günler REST API'den
sayfalanarak çekilir. REST için birden fazla adres sırayla denenir; bazı
bölgelerde `api.binance.com` erişimi kısıtlıdır (HTTP 451).
"""

from __future__ import annotations

import hashlib
import io
import time
import zipfile
from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd
import requests

from ..config import INTERVAL_MS

ARCHIVE_BASE = "https://data.binance.vision/data/spot/monthly/klines"

REST_HOSTS: tuple[str, ...] = (
    "https://api.binance.com",
    "https://data-api.binance.vision",
    "https://www.binance.com",
)

RAW_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]

FLOAT_COLUMNS = ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]

REST_LIMIT = 1000

Progress = Callable[[str], None]


class DataError(RuntimeError):
    """Veri indirilemedi veya doğrulanamadı."""


def to_milliseconds(values: pd.Series | np.ndarray) -> np.ndarray:
    """Zaman damgalarını milisaniyeye çevirir.

    Binance spot arşivleri 2025'ten itibaren mikrosaniye kullanır; daha
    eskileri ve REST API milisaniyedir. Milisaniye cinsinden bugünün değeri
    ~1,7e12, mikrosaniye ~1,7e15'tir; 1e14 eşiği ikisini güvenle ayırır.
    """
    arr = np.asarray(values, dtype=np.int64)
    return np.where(arr > 100_000_000_000_000, arr // 1000, arr)


def parse_klines(raw: pd.DataFrame | Sequence[Sequence]) -> pd.DataFrame:
    """Ham kline satırlarını UTC zaman indeksli OHLCV tablosuna çevirir."""
    frame = raw if isinstance(raw, pd.DataFrame) else pd.DataFrame(list(raw))
    if frame.empty:
        return empty_frame()
    frame = frame.iloc[:, : len(RAW_COLUMNS)].copy()
    frame.columns = RAW_COLUMNS[: frame.shape[1]]

    # Bazı arşivlerde başlık satırı bulunur.
    first = str(frame.iloc[0, 0])
    if not first.lstrip("-").isdigit():
        frame = frame.iloc[1:]

    open_ms = to_milliseconds(pd.to_numeric(frame["open_time"]).to_numpy())
    close_ms = to_milliseconds(pd.to_numeric(frame["close_time"]).to_numpy())
    out = pd.DataFrame(
        {col: pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float) for col in FLOAT_COLUMNS}
    )
    out["trades"] = pd.to_numeric(frame["trades"], errors="coerce").fillna(0).to_numpy(dtype=np.int64)
    out["close_time"] = pd.to_datetime(close_ms, unit="ms", utc=True)
    out.index = pd.DatetimeIndex(pd.to_datetime(open_ms, unit="ms", utc=True), name="open_time")
    out = out[["open", "high", "low", "close", "volume", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "close_time"]]
    return out[~out.index.duplicated(keep="last")].sort_index()


def empty_frame() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            **{col: pd.Series(dtype=float) for col in ["open", "high", "low", "close", "volume", "quote_volume"]},
            "trades": pd.Series(dtype=np.int64),
            "taker_buy_base": pd.Series(dtype=float),
            "taker_buy_quote": pd.Series(dtype=float),
            "close_time": pd.Series(dtype="datetime64[ns, UTC]"),
        }
    )
    frame.index = pd.DatetimeIndex([], tz="UTC", name="open_time")
    return frame


def archive_url(symbol: str, interval: str, year: int, month: int) -> str:
    name = f"{symbol}-{interval}-{year:04d}-{month:02d}.zip"
    return f"{ARCHIVE_BASE}/{symbol}/{interval}/{name}"


def fetch_month_archive(
    session: requests.Session,
    symbol: str,
    interval: str,
    year: int,
    month: int,
    verify: bool = True,
    timeout: float = 60.0,
) -> pd.DataFrame | None:
    """Bir aylık arşivi indirir. Arşiv yoksa (404) `None` döner."""
    url = archive_url(symbol, interval, year, month)
    response = session.get(url, timeout=timeout)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    payload = response.content

    if verify:
        checksum = session.get(url + ".CHECKSUM", timeout=timeout)
        if checksum.status_code == 200:
            expected = checksum.text.split()[0].strip().lower()
            actual = hashlib.sha256(payload).hexdigest()
            if expected != actual:
                raise DataError(f"SHA256 uyuşmuyor: {url}")

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if not names:
            raise DataError(f"arşivde CSV yok: {url}")
        raw = pd.read_csv(archive.open(names[0]), header=None, dtype=str)
    return parse_klines(raw)


class RestClient:
    """Kline uç noktası için adres yedekli, sayfalayan istemci."""

    def __init__(
        self,
        session: requests.Session | None = None,
        hosts: Sequence[str] = REST_HOSTS,
        timeout: float = 20.0,
        pause: float = 0.1,
    ) -> None:
        self.session = session or requests.Session()
        self.hosts = list(hosts)
        self.timeout = timeout
        self.pause = pause
        self._working: str | None = None

    def _get(self, params: dict) -> list:
        order = ([self._working] if self._working else []) + [h for h in self.hosts if h != self._working]
        errors: list[str] = []
        for host in order:
            try:
                response = self.session.get(f"{host}/api/v3/klines", params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                errors.append(f"{host}: {exc.__class__.__name__}")
                continue
            if response.status_code == 200:
                self._working = host
                return response.json()
            if response.status_code == 429:
                # Hız sınırı: kısa bekleyip aynı adresi bir kez daha dene.
                time.sleep(float(response.headers.get("Retry-After", "2")))
                response = self.session.get(f"{host}/api/v3/klines", params=params, timeout=self.timeout)
                if response.status_code == 200:
                    self._working = host
                    return response.json()
            errors.append(f"{host}: HTTP {response.status_code}")
        raise DataError("REST verisi alınamadı (" + "; ".join(errors) + ")")

    def klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int | None = None,
        progress: Progress | None = None,
    ) -> pd.DataFrame:
        """`start_ms`'den itibaren (dahil) bütün mumları sayfalayarak çeker."""
        step = INTERVAL_MS[interval]
        rows: list = []
        cursor = int(start_ms)
        while True:
            params = {"symbol": symbol, "interval": interval, "startTime": cursor, "limit": REST_LIMIT}
            if end_ms is not None:
                params["endTime"] = int(end_ms)
            batch = self._get(params)
            if not batch:
                break
            rows.extend(batch)
            last_open = int(batch[-1][0])
            if progress is not None:
                stamp = pd.to_datetime(last_open, unit="ms", utc=True).strftime("%Y-%m-%d %H:%M")
                progress(f"{symbol} {interval}: {stamp} UTC'ye kadar alındı")
            if len(batch) < REST_LIMIT:
                break
            cursor = last_open + step
            if end_ms is not None and cursor > end_ms:
                break
            if self.pause:
                time.sleep(self.pause)
        return parse_klines(rows)
