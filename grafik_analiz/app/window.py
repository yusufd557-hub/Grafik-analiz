"""Ana pencere."""

from __future__ import annotations

import math
import traceback
from collections.abc import Callable

import requests
from PySide6 import QtCore, QtGui, QtWidgets

from ..analysis import AnalysisResult, analyze
from ..config import INTERVAL_NAMES, INTERVALS, SYMBOLS
from ..data import CandleStore, DataError
from ..patterns.base import BROKEN, FORMING, RESOLVED, Formation
from ..report import DIRECTION_NAMES, percent, price, scale_name, summary_text
from ..stats import lookup
from .chart import DOWN, NEUTRAL, UP, ChartWidget

ARROWS = {1: "↑", -1: "↓", 0: "↕"}


class _Signals(QtCore.QObject):
    progress = QtCore.Signal(str)
    done = QtCore.Signal(object)
    failed = QtCore.Signal(str)


class Task(QtCore.QRunnable):
    """Arka plan işi. `fn(..., progress=callable)` imzalı bir fonksiyon çalıştırır."""

    def __init__(self, fn: Callable, *args) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.signals = _Signals()

    def run(self) -> None:
        try:
            result = self.fn(*self.args, progress=self.signals.progress.emit)
        except Exception as exc:  # noqa: BLE001 — hata kullanıcıya gösterilir
            self.signals.failed.emit(f"{exc}\n\n{traceback.format_exc()}")
        else:
            self.signals.done.emit(result)


def load_and_analyze(
    symbol: str, interval: str, refresh: bool, progress: Callable[[str], None]
) -> tuple[AnalysisResult, str | None]:
    """Veriyi (gerekirse) günceller ve analiz eder. İkinci değer kullanıcıya gösterilecek uyarıdır."""
    store = CandleStore()
    frame = store.load(symbol, interval)
    warning = None
    if refresh or frame.empty:
        try:
            frame = store.update(symbol, interval, progress=progress)
        except (DataError, requests.RequestException) as exc:
            if frame.empty:
                raise
            warning = f"veri güncellenemedi ({exc}); kayıtlı veri gösteriliyor"
    progress(f"{symbol} {interval}: analiz ediliyor…")
    return analyze(frame, symbol, interval), warning


def _item(text: str, color: str | None = None, align_right: bool = False, data=None) -> QtWidgets.QTableWidgetItem:
    item = QtWidgets.QTableWidgetItem(text)
    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
    if color:
        item.setForeground(QtGui.QColor(color))
    if align_right:
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
    if data is not None:
        item.setData(QtCore.Qt.UserRole, data)
    return item


def _table(headers: list[str]) -> QtWidgets.QTableWidget:
    table = QtWidgets.QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)
    table.setWordWrap(False)
    return table


def _dir_color(d: int) -> str:
    return UP if d > 0 else DOWN if d < 0 else NEUTRAL


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Grafik Analiz")
        self.resize(1500, 900)
        self.result: AnalysisResult | None = None
        self._request = 0
        self._tasks: set[Task] = set()

        self.chart = ChartWidget()
        self._build_toolbar()
        self._build_tabs()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(self.chart)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([1000, 560])
        self.setCentralWidget(splitter)
        self.status = QtWidgets.QLabel("Hazır")
        self.statusBar().addWidget(self.status, 1)

    # ------------------------------------------------------------ arayüz

    def _build_toolbar(self) -> None:
        bar = self.addToolBar("Kontroller")
        bar.setMovable(False)
        self.symbol_box = QtWidgets.QComboBox()
        for s in SYMBOLS:
            self.symbol_box.addItem(s.replace("USDT", "/USDT"), s)
        self.interval_box = QtWidgets.QComboBox()
        for i in INTERVALS:
            self.interval_box.addItem(INTERVAL_NAMES[i], i)
        self.interval_box.setCurrentIndex(INTERVALS.index("4h"))
        self.refresh_button = QtWidgets.QPushButton("Verileri güncelle")
        self.bars_box = QtWidgets.QSpinBox()
        self.bars_box.setRange(200, 50_000)
        self.bars_box.setSingleStep(500)
        self.bars_box.setValue(1500)
        self.bars_box.setSuffix(" mum")

        bar.addWidget(QtWidgets.QLabel(" Coin "))
        bar.addWidget(self.symbol_box)
        bar.addWidget(QtWidgets.QLabel("  Zaman dilimi "))
        bar.addWidget(self.interval_box)
        bar.addWidget(QtWidgets.QLabel("  Gösterilen "))
        bar.addWidget(self.bars_box)
        bar.addSeparator()
        bar.addWidget(self.refresh_button)
        bar.addSeparator()

        self.overlay_boxes: dict[str, QtWidgets.QCheckBox] = {}
        for key, label in (
            ("ema", "EMA"),
            ("pivots", "Pivotlar"),
            ("levels", "Destek/Direnç"),
            ("trendlines", "Trend çizgileri"),
            ("fibonacci", "Fibonacci"),
            ("formations", "Formasyonlar"),
            ("candles", "Mum formasyonları"),
        ):
            box = QtWidgets.QCheckBox(label)
            box.setChecked(getattr(self.chart.overlays, key))
            box.toggled.connect(lambda checked, k=key: self._toggle_overlay(k, checked))
            bar.addWidget(box)
            self.overlay_boxes[key] = box

        self.symbol_box.currentIndexChanged.connect(lambda _i: self.load(refresh=True))
        self.interval_box.currentIndexChanged.connect(lambda _i: self.load(refresh=True))
        self.refresh_button.clicked.connect(lambda: self.load(refresh=True))
        self.bars_box.editingFinished.connect(self._redisplay)

    def _build_tabs(self) -> None:
        self.tabs = QtWidgets.QTabWidget()

        self.summary = QtWidgets.QPlainTextEdit()
        self.summary.setReadOnly(True)
        font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        self.summary.setFont(font)
        self.tabs.addTab(self.summary, "Özet")

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        self.formation_filter = QtWidgets.QComboBox()
        self.formation_filter.addItems(["Aktif", "Sonuçlanan", "Hepsi"])
        self.formation_filter.currentIndexChanged.connect(lambda _i: self._fill_formations())
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Göster:"))
        top.addWidget(self.formation_filter)
        top.addStretch(1)
        layout.addLayout(top)
        self.formation_table = _table(["Tespit (UTC)", "Formasyon", "Durum", "Yön", "Giriş / tetik", "Hedef", "Stop", "Geçmiş hedef oranı"])
        self.formation_table.itemSelectionChanged.connect(self._formation_selected)
        layout.addWidget(self.formation_table)
        hint = QtWidgets.QLabel("Bir satıra tıklayınca grafik o formasyona gider.")
        hint.setStyleSheet("color: #787b86")
        layout.addWidget(hint)
        self.tabs.addTab(page, "Formasyonlar")

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        note = QtWidgets.QLabel(
            "Hedef payı: kırılımdan sonra hedef ya da stoptan birine ulaşanlar içinde hedefin payı, "
            "hedef / (hedef + stop). Süresi dolanlar ayrı sayılır. Rastgele kıyas: aynı hedef ve stop "
            "uzaklıklarıyla yönsüz bir fiyatın hedefe önce ulaşma olasılığı, S/(H+S). "
            "Mum formasyonlarında isabet, birkaç bar sonra fiyatın beklenen yönde olma oranıdır; "
            "taban, aynı dönemde koşulsuz orandır."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #9598a1")
        layout.addWidget(note)
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.stats_table = _table(["Formasyon", "Yön", "Tespit", "Kırılım", "Hedef", "Stop", "Süre doldu", "Hedef payı", "%95 aralık", "Rastgele kıyas"])
        self.candle_stats_table = _table(["Mum formasyonu", "Yön", "Örnek", "İsabet", "Taban", "Fark"])
        split.addWidget(self.stats_table)
        split.addWidget(self.candle_stats_table)
        layout.addWidget(split)
        self.tabs.addTab(page, "İstatistik")

        self.candle_table = _table(["Zaman (UTC)", "Mum formasyonu", "Yön", "Geçmiş isabet / taban"])
        self.candle_table.itemSelectionChanged.connect(self._candle_selected)
        self.tabs.addTab(self.candle_table, "Mum formasyonları")

    # ------------------------------------------------------------ veri akışı

    @property
    def symbol(self) -> str:
        return self.symbol_box.currentData()

    @property
    def interval(self) -> str:
        return self.interval_box.currentData()

    def load(self, refresh: bool = False) -> None:
        self._request += 1
        request = self._request
        self.refresh_button.setEnabled(False)
        self.status.setText(f"{self.symbol} {self.interval}: yükleniyor…")
        task = Task(load_and_analyze, self.symbol, self.interval, refresh)
        task.signals.progress.connect(lambda msg, r=request: r == self._request and self.status.setText(msg))
        task.signals.done.connect(lambda result, r=request, t=task: self._on_done(result, r, t))
        task.signals.failed.connect(lambda err, r=request, t=task: self._on_failed(err, r, t))
        self._tasks.add(task)
        QtCore.QThreadPool.globalInstance().start(task)

    def _on_done(self, outcome: tuple[AnalysisResult, str | None], request: int, task: Task) -> None:
        self._tasks.discard(task)
        if request != self._request:
            return
        self.refresh_button.setEnabled(True)
        result, warning = outcome
        self.show_result(result)
        if warning:
            self.status.setText(self.status.text() + " · ⚠ " + warning)

    def _on_failed(self, error: str, request: int, task: Task) -> None:
        self._tasks.discard(task)
        if request != self._request:
            return
        self.refresh_button.setEnabled(True)
        self.status.setText("Hata: " + error.splitlines()[0])
        QtWidgets.QMessageBox.warning(self, "Veri veya analiz hatası", error)

    def show_result(self, result: AnalysisResult) -> None:
        self.result = result
        self.chart.selected = None
        self.chart.set_result(result, self.bars_box.value())
        self.summary.setPlainText(summary_text(result))
        self._fill_formations()
        self._fill_stats()
        self._fill_candles()
        last = result.frame.index[-1]
        self.status.setText(
            f"{result.symbol} · {INTERVAL_NAMES.get(result.interval, result.interval)} · "
            f"{len(result.frame):,} mum analiz edildi · son kapanmış mum {last:%Y-%m-%d %H:%M} UTC".replace(",", ".")
        )

    def _redisplay(self) -> None:
        if self.result is not None:
            self.chart.set_result(self.result, self.bars_box.value(), keep_view=True)

    def _toggle_overlay(self, key: str, checked: bool) -> None:
        setattr(self.chart.overlays, key, checked)
        self.chart.redraw_overlays()

    # ------------------------------------------------------------ tablolar

    def _history(self, f: Formation, d: int) -> str:
        row = lookup(self.result.formation_stats, f.key, d)
        if row is None or row["decided"] == 0:
            return "örnek yok"
        return f"{percent(row['hit_rate'])} ({int(row['decided'])} örnek; kıyas {percent(row['baseline'])})"

    def _fill_formations(self) -> None:
        table = self.formation_table
        table.setRowCount(0)
        if self.result is None:
            return
        t = self.result.as_of
        mode = self.formation_filter.currentText()
        rows = []
        for f in reversed(self.result.formations):
            status = f.status_at(t)
            if mode == "Aktif" and status not in (FORMING, BROKEN):
                continue
            if mode == "Sonuçlanan" and status not in RESOLVED:
                continue
            rows.append((f, status))
            if len(rows) >= 400:
                break
        table.setRowCount(len(rows))
        index = self.result.frame.index
        for r, (f, status) in enumerate(rows):
            when = index[f.detected_index].strftime("%Y-%m-%d %H:%M")
            table.setItem(r, 0, _item(when, data=f))
            table.setItem(r, 1, _item(f"{f.name} ({scale_name(f.scale)})"))
            table.setItem(r, 2, _item(status))
            if f.breakout_index is not None:
                d = f.direction
                table.setItem(r, 3, _item(f"{ARROWS[d]} {DIRECTION_NAMES[d]}", _dir_color(d)))
                table.setItem(r, 4, _item(price(f.breakout_price), align_right=True))
                table.setItem(r, 5, _item(price(f.target), _dir_color(d), align_right=True))
                table.setItem(r, 6, _item(price(f.stop), align_right=True))
                table.setItem(r, 7, _item(self._history(f, d)))
            else:
                pending = f.pending_levels(t) if status == FORMING else {}
                table.setItem(r, 3, _item(f"{ARROWS[f.bias]} {DIRECTION_NAMES[f.bias]}", _dir_color(f.bias)))
                table.setItem(r, 4, _item(" / ".join(f"{ARROWS[d]} {price(v['trigger'])}" for d, v in pending.items()), align_right=True))
                table.setItem(r, 5, _item(" / ".join(f"{ARROWS[d]} {price(v['target'])}" for d, v in pending.items()), align_right=True))
                table.setItem(r, 6, _item(" / ".join(f"{ARROWS[d]} {price(v['stop'])}" for d, v in pending.items()), align_right=True))
                table.setItem(r, 7, _item(" / ".join(f"{ARROWS[d]} {self._history(f, d)}" for d in pending) if pending else ""))
        table.resizeColumnsToContents()

    def _formation_selected(self) -> None:
        items = self.formation_table.selectedItems()
        if not items or self.result is None:
            return
        f = self.formation_table.item(items[0].row(), 0).data(QtCore.Qt.UserRole)
        needed = len(self.result.frame) - f.start_index + 60
        if needed > self.bars_box.value():
            self.bars_box.setValue(min(needed, self.bars_box.maximum()))
            self.chart.set_result(self.result, self.bars_box.value())
        self.chart.focus(f)

    def _fill_stats(self) -> None:
        stats = self.result.formation_stats
        table = self.stats_table
        table.setRowCount(len(stats))
        for r, row in enumerate(stats.itertuples()):
            d = int(row.direction)
            table.setItem(r, 0, _item(row.name))
            table.setItem(r, 1, _item(f"{ARROWS[d]} {DIRECTION_NAMES[d]}", _dir_color(d)))
            table.setItem(r, 2, _item(str(row.detected), align_right=True))
            table.setItem(r, 3, _item(str(row.breakouts), align_right=True))
            table.setItem(r, 4, _item(str(row.target), align_right=True))
            table.setItem(r, 5, _item(str(row.stop), align_right=True))
            table.setItem(r, 6, _item(str(row.timeout), align_right=True))
            # Renk yalnızca güven aralığı kıyası tamamen dışarıda bırakıyorsa verilir.
            color = None
            if math.isfinite(row.baseline) and math.isfinite(row.ci_low):
                color = UP if row.ci_low > row.baseline else DOWN if row.ci_high < row.baseline else None
            table.setItem(r, 7, _item(percent(row.hit_rate), color, align_right=True))
            table.setItem(r, 8, _item(f"{percent(row.ci_low)}–{percent(row.ci_high)}", align_right=True))
            table.setItem(r, 9, _item(percent(row.baseline), align_right=True))
        table.resizeColumnsToContents()

        cstats = self.result.candle_stats
        table = self.candle_stats_table
        table.setRowCount(len(cstats))
        for r, row in enumerate(cstats.itertuples()):
            d = int(row.bias)
            table.setItem(r, 0, _item(row.name))
            table.setItem(r, 1, _item(f"{ARROWS[d]} {DIRECTION_NAMES[d]}", _dir_color(d)))
            table.setItem(r, 2, _item(str(row.count), align_right=True))
            table.setItem(r, 3, _item(percent(row.success), align_right=True))
            table.setItem(r, 4, _item(percent(row.base), align_right=True))
            edge = row.edge
            text = "–" if not math.isfinite(edge) else f"{100 * edge:+.1f} puan".replace(".", ",")
            color = None if not math.isfinite(edge) else (UP if edge > 0 else DOWN)
            table.setItem(r, 5, _item(text, color, align_right=True))
        table.resizeColumnsToContents()

    def _fill_candles(self) -> None:
        result = self.result
        events = list(reversed(result.candle_events(max(0, result.as_of - 300))))
        stats = result.candle_stats.set_index("key")
        table = self.candle_table
        table.setRowCount(len(events))
        for r, e in enumerate(events):
            d = e.spec.bias
            table.setItem(r, 0, _item(result.frame.index[e.index].strftime("%Y-%m-%d %H:%M"), data=e.index))
            table.setItem(r, 1, _item(e.spec.name))
            table.setItem(r, 2, _item(f"{ARROWS[d]} {DIRECTION_NAMES[d]}", _dir_color(d)))
            row = stats.loc[e.spec.key]
            text = "–" if d == 0 else f"{percent(row['success'])} / {percent(row['base'])} ({int(row['count'])} örnek)"
            table.setItem(r, 3, _item(text))
        table.resizeColumnsToContents()

    def _candle_selected(self) -> None:
        items = self.candle_table.selectedItems()
        if not items or self.result is None:
            return
        index = self.candle_table.item(items[0].row(), 0).data(QtCore.Qt.UserRole)
        x = self.chart.x(index)
        self.chart.price.setXRange(x - 60, x + 20, padding=0)
