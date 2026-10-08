"""Yerel mum önbelleği ve artımlı güncelleme.

Spot mumları `veri/<COIN>/<dilim>.parquet`, vadeli mumları
`veri/vadeli/<COIN>/<dilim>.parquet`, fonlama oranları
`veri/vadeli/<COIN>/fonlama.parquet` dosyasında tutulur.
Güncelleme yalnızca eksik kısmı indirir: tamamlanmış aylar arşivden, kalan
son günler REST API'den gelir. Henüz kapanmamış mum hiçbir zaman kaydedilmez;
analiz yalnızca kapanmış mumlarla çalışır.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests

from ..config import DEFAULT_HISTORY_START, INTERVAL_MS, data_dir, validate_interval, validate_symbol
from .binance import (
    FUTURES,
    MARKETS,
    SPOT,
    DataError,
    Progress,
    RestClient,
    empty_frame,
    empty_funding,
    fetch_month_archive,
    fetch_month_funding,
)

# Bu sayıdan az eksik mum REST'ten alınır (1000 mum/istek); fazlası arşivden.
REST_ONLY_MAX_BARS = 10_000
ARCHIVE_WORKERS = 8
ARCHIVE_RETRIES = 3


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
        market: str = SPOT,
    ) -> None:
        if market not in MARKETS:
            raise ValueError(f"bilinmeyen piyasa: {market}")
        self.market = market
        self.root = Path(root) if root is not None else data_dir()
        # Dışarıdan oturum verilirse (ör. testler) arşiv indirmeleri de onu kullanır;
        # verilmezse her iş parçacığı kendi oturumunu açar.
        self._shared_session = session
        self.session = session or requests.Session()
        self.rest = rest or RestClient(session=self.session, market=market)

    def _base(self, symbol: str) -> Path:
        base = self.root / "vadeli" if self.market == FUTURES else self.root
        return base / validate_symbol(symbol)

    def path(self, symbol: str, interval: str) -> Path:
        return self._base(symbol) / f"{validate_interval(interval)}.parquet"

    def funding_path(self, symbol: str) -> Path:
        return self._base(symbol) / "fonlama.parquet"

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
            if self._shared_session is not None:
                return self._shared_session
            if not hasattr(local, "session"):
                local.session = requests.Session()
            return local.session

        def one(ym: tuple[int, int]) -> pd.DataFrame | None:
            year, month = ym
            for attempt in range(ARCHIVE_RETRIES):
                try:
                    return fetch_month_archive(session(), symbol, interval, year, month, market=self.market)
                except (requests.RequestException, DataError) as exc:
                    if attempt + 1 == ARCHIVE_RETRIES:
                        say(f"{symbol} {interval}: {year}-{month:02d} arşivi alınamadı ({exc})")
                        return None
                    time.sleep(2**attempt)
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
            try:
                recent = self.rest.klines(symbol, interval, start_ms, progress=say)
            except DataError as exc:
                if not parts:
                    raise
                # Arşivden gelen kısım yine de kaydedilir; eksik son günler bir
                # sonraki güncellemede tamamlanır.
                say(f"{symbol} {interval}: son mumlar alınamadı ({exc})")
                recent = None
            if recent is not None and not recent.empty:
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

    # ------------------------------------------------------------ fonlama

    def load_funding(self, symbol: str) -> pd.DataFrame:
        path = self.funding_path(symbol)
        if not path.exists():
            return empty_funding()
        frame = pd.read_parquet(path)
        frame.index = pd.DatetimeIndex(frame.index, name="funding_time")
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        return frame.sort_index()

    def update_funding(
        self,
        symbol: str,
        start: str = "2019-09",
        now: pd.Timestamp | None = None,
        progress: Progress | None = None,
    ) -> pd.DataFrame:
        """Vadeli fonlama oranlarını bugüne kadar tamamlar."""
        if self.market != FUTURES:
            raise ValueError("fonlama yalnızca vadeli piyasada vardır")
        symbol = validate_symbol(symbol)
        now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
        say = progress or (lambda _msg: None)
        existing = self.load_funding(symbol)
        first = pd.Timestamp(start + "-01", tz="UTC") if existing.empty else existing.index[-1] + pd.Timedelta(seconds=1)
        parts = [existing] if not existing.empty else []
        next_time = first

        months = _months_between(first, _month_start(now))
        if len(months) > 2:
            local = threading.local()

            def one(ym: tuple[int, int]) -> pd.DataFrame | None:
                if self._shared_session is not None:
                    sess = self._shared_session
                else:
                    if not hasattr(local, "session"):
                        local.session = requests.Session()
                    sess = local.session
                try:
                    return fetch_month_funding(sess, symbol, *ym)
                except (requests.RequestException, DataError) as exc:
                    say(f"{symbol} fonlama {ym[0]}-{ym[1]:02d} alınamadı ({exc})")
                    return None

            with ThreadPoolExecutor(max_workers=ARCHIVE_WORKERS) as pool:
                chunks = list(pool.map(one, months))
            started = not existing.empty
            for chunk in chunks:
                if chunk is None or chunk.empty:
                    if started:
                        break
                    continue
                started = True
                parts.append(chunk)
                next_time = max(next_time, chunk.index[-1] + pd.Timedelta(seconds=1))

        try:
            recent = self.rest.funding(symbol, int(next_time.value // 1_000_000))
            if not recent.empty:
                parts.append(recent)
        except DataError as exc:
            if not parts:
                raise
            say(f"{symbol} fonlama: son kayıtlar alınamadı ({exc})")

        if not parts:
            raise DataError(f"{symbol} fonlama verisi bulunamadı")
        frame = pd.concat(parts)
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        frame = frame[frame.index <= now]
        path = self.funding_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        frame.to_parquet(tmp)
        tmp.replace(path)
        say(f"{symbol} fonlama: {len(frame):,} kayıt ({frame.index[0]:%Y-%m-%d} – {frame.index[-1]:%Y-%m-%d %H:%M} UTC)")
        return frame
