"""Yerel mum önbelleği ve artımlı güncelleme.

Her coin/zaman dilimi çifti `veri/<COIN>/<dilim>.parquet` dosyasında tutulur.
Güncelleme yalnızca eksik kısmı indirir: tamamlanmış aylar arşivden, kalan
son günler REST API'den gelir. Henüz kapanmamış mum hiçbir zaman kaydedilmez;
analiz yalnızca kapanmış mumlarla çalışır.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

from ..config import DEFAULT_HISTORY_START, INTERVAL_MS, data_dir, validate_interval, validate_symbol
from .binance import DataError, Progress, RestClient, empty_frame, fetch_month_archive

# Bu sayıdan az eksik mum REST'ten alınır (1000 mum/istek); fazlası arşivden.
REST_ONLY_MAX_BARS = 10_000
ARCHIVE_WORKERS = 8


def _month_start(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=ts.year, month=ts.month, day=1, tz="UTC")


def _months_between(first: pd.Timestamp, last_exclusive: pd.Timestamp) -> list[tuple[int, int]]:
    months = []
    cursor = _month_start(first)
    while cursor < last_exclusive:
        months.append((cursor.year, cursor.month))
        cursor = cursor + pd.offsets.MonthBegin(1)
    return months


def find_gaps(frame: pd.DataFrame, interval: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Ardışık mumlar arasında bir dilimden uzun boşlukları listeler.

    Binance'in bakım kesintileri gerçek boşluk üretir; bunlar hata değildir
    ama bilinmesi gerekir.
    """
    if len(frame) < 2:
        return []
    step = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
    diffs = frame.index.to_series().diff()
    mask = diffs > step
    return [(frame.index[i - 1], frame.index[i]) for i in range(len(frame)) if mask.iloc[i]]


class CandleStore:
    def __init__(
        self,
        root: Path | None = None,
        session: requests.Session | None = None,
        rest: RestClient | None = None,
    ) -> None:
        self.root = Path(root) if root is not None else data_dir()
        self.session = session or requests.Session()
        self.rest = rest or RestClient(session=self.session)

    def path(self, symbol: str, interval: str) -> Path:
        return self.root / validate_symbol(symbol) / f"{validate_interval(interval)}.parquet"

    def load(self, symbol: str, interval: str) -> pd.DataFrame:
        path = self.path(symbol, interval)
        if not path.exists():
            return empty_frame()
        frame = pd.read_parquet(path)
        frame.index = pd.DatetimeIndex(frame.index, name="open_time")
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        return frame.sort_index()

    def save(self, symbol: str, interval: str, frame: pd.DataFrame) -> Path:
        path = self.path(symbol, interval)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        frame.to_parquet(tmp)
        tmp.replace(path)
        return path

    def _fetch_archives(
        self,
        symbol: str,
        interval: str,
        months: list[tuple[int, int]],
        say: Progress,
    ) -> list[pd.DataFrame | None]:
        """Ay arşivlerini paralel indirir; sıra korunur, hata `None` sayılır."""
        local = threading.local()

        def session() -> requests.Session:
            if not hasattr(local, "session"):
                local.session = requests.Session()
            return local.session

        def one(ym: tuple[int, int]) -> pd.DataFrame | None:
            year, month = ym
            try:
                return fetch_month_archive(session(), symbol, interval, year, month)
            except (requests.RequestException, DataError) as exc:
                say(f"{symbol} {interval}: {year}-{month:02d} arşivi alınamadı ({exc})")
                return None

        results: list[pd.DataFrame | None] = [None] * len(months)
        with ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as pool:
            futures = {pool.submit(one, ym): i for i, ym in enumerate(months)}
            done = 0
            for future in as_completed(futures):
                results[futures[future]] = future.result()
                done += 1
                if done % 10 == 0 or done == len(months):
                    say(f"{symbol} {interval}: arşiv {done}/{len(months)}")
        return results

    def update(
        self,
        symbol: str,
        interval: str,
        start: str | None = None,
        now: pd.Timestamp | None = None,
        progress: Progress | None = None,
    ) -> pd.DataFrame:
        """Önbelleği bugüne kadar tamamlar ve tüm seriyi döndürür."""
        symbol = validate_symbol(symbol)
        interval = validate_interval(interval)
        now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
        step = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
        say = progress or (lambda _msg: None)

        existing = self.load(symbol, interval)
        if existing.empty:
            first_needed = pd.Timestamp(start or DEFAULT_HISTORY_START[interval] + "-01", tz="UTC")
        else:
            first_needed = existing.index[-1] + step

        parts = [existing] if not existing.empty else []
        next_open = first_needed
        missing_bars = max(0, int((now - first_needed) / step))

        # 1) Uzun geçmiş: tamamlanmış aylar resmî arşivden, paralel indirilir.
        #    Az sayıda eksik mum için doğrudan REST daha hızlıdır.
        current_month = _month_start(now)
        months = _months_between(first_needed, current_month)
        if months and missing_bars > REST_ONLY_MAX_BARS:
            say(f"{symbol} {interval}: {len(months)} aylık arşiv indiriliyor")
            chunks = self._fetch_archives(symbol, interval, months, say)
            # Arşivler kesintisiz bir dizi oluşturmalı: listelenmeden önceki
            # aylar boş gelir; listelendikten sonraki ilk eksik ayda durulur,
            # oradan sonrası REST'ten tamamlanır.
            started = not existing.empty
            for (year, month), chunk in zip(months, chunks):
                if chunk is None:
                    if started:
                        break
                    continue
                started = True
                parts.append(chunk)
                next_open = max(next_open, chunk.index[-1] + step)

        # 2) Kalan kısım: REST API.
        if next_open + step <= now:
            say(f"{symbol} {interval}: son mumlar REST API'den alınıyor")
            start_ms = int(next_open.value // 1_000_000)
            recent = self.rest.klines(symbol, interval, start_ms, progress=say)
            if not recent.empty:
                parts.append(recent)

        if not parts:
            raise DataError(f"{symbol} {interval} için veri bulunamadı")

        frame = pd.concat(parts)
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        # Kapanmamış mum: kapanış zamanı henüz gelmemiş olan.
        frame = frame[frame["close_time"] < now]
        frame = frame[frame.index >= first_needed] if existing.empty else frame

        self.save(symbol, interval, frame)
        gaps = find_gaps(frame, interval)
        say(
            f"{symbol} {interval}: {len(frame):,} mum hazır "
            f"({frame.index[0]:%Y-%m-%d} – {frame.index[-1]:%Y-%m-%d %H:%M} UTC)"
            + (f", {len(gaps)} veri boşluğu" if gaps else "")
        )
        return frame
