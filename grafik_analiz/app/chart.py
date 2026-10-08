"""Mum grafiği ve analiz katmanları (pyqtgraph)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6 import QtCore, QtGui

from ..analysis import AnalysisResult
from ..patterns.base import BROKEN, FORMING, RESOLVED, Formation
from ..report import price as fmt_price

UP = "#26a69a"
DOWN = "#ef5350"
NEUTRAL = "#f0b429"
TEXT = "#d1d4dc"
GRID = "#2a2e39"
BACKGROUND = "#131722"
PIVOT = "#7e57c2"
LEVEL_SUPPORT = "#2e7d32"
LEVEL_RESIST = "#c62828"
FIB = "#5c6bc0"
EMA_COLORS = {"ema20": "#ffb74d", "ema50": "#4fc3f7", "ema200": "#ba68c8"}

pg.setConfigOptions(antialias=True, background=BACKGROUND, foreground=TEXT)


def direction_color(d: int) -> str:
    return UP if d > 0 else DOWN if d < 0 else NEUTRAL


class TimeAxis(pg.AxisItem):
    """Bar sırasını (x) tarih/saat etiketine çevirir; hafta sonu/boşluk sorunu olmaz."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.times: pd.DatetimeIndex | None = None
        self.daily = False

    def tickStrings(self, values, scale, spacing):  # noqa: N802 (Qt adı)
        if self.times is None or len(self.times) == 0:
            return [""] * len(values)
        out = []
        fmt = "%d.%m.%Y" if self.daily else "%d.%m %H:%M"
        for v in values:
            i = int(round(v))
            out.append(self.times[i].strftime(fmt) if 0 <= i < len(self.times) else "")
        return out


class CandlestickItem(pg.GraphicsObject):
    def __init__(self) -> None:
        super().__init__()
        self.picture = QtGui.QPicture()
        self.ohlc = np.empty((0, 4))
        self._rect = QtCore.QRectF()

    def set_data(self, ohlc: np.ndarray) -> None:
        self.ohlc = np.asarray(ohlc, dtype=float)
        self.picture = QtGui.QPicture()
        painter = QtGui.QPainter(self.picture)
        width = 0.35
        up_pen, down_pen = pg.mkPen(UP), pg.mkPen(DOWN)
        up_brush, down_brush = pg.mkBrush(UP), pg.mkBrush(DOWN)
        for x, (o, h, l, c) in enumerate(self.ohlc):
            rising = c >= o
            painter.setPen(up_pen if rising else down_pen)
            painter.drawLine(QtCore.QPointF(x, l), QtCore.QPointF(x, h))
            painter.setBrush(up_brush if rising else down_brush)
            top, bottom = max(o, c), min(o, c)
            painter.drawRect(QtCore.QRectF(x - width, bottom, 2 * width, max(top - bottom, 1e-12)))
        painter.end()
        if len(self.ohlc):
            lo, hi = float(np.nanmin(self.ohlc[:, 2])), float(np.nanmax(self.ohlc[:, 1]))
            self._rect = QtCore.QRectF(-1, lo, len(self.ohlc) + 1, hi - lo)
        else:
            self._rect = QtCore.QRectF()
        self.prepareGeometryChange()
        self.informViewBoundsChanged()
        self.update()

    def paint(self, painter, *args) -> None:
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self) -> QtCore.QRectF:  # noqa: N802
        return self._rect

    def dataBounds(self, ax, frac=1.0, orthoRange=None):  # noqa: N802, N803
        """Görünen x aralığındaki en düşük/en yüksek fiyat (y otomatik ölçek için)."""
        if len(self.ohlc) == 0:
            return None, None
        if ax == 0:
            return -1, len(self.ohlc)
        if orthoRange is None:
            return float(np.nanmin(self.ohlc[:, 2])), float(np.nanmax(self.ohlc[:, 1]))
        lo = max(0, int(np.floor(orthoRange[0])))
        hi = min(len(self.ohlc), int(np.ceil(orthoRange[1])) + 1)
        if hi <= lo:
            return None, None
        seg = self.ohlc[lo:hi]
        return float(np.nanmin(seg[:, 2])), float(np.nanmax(seg[:, 1]))


@dataclass
class Overlays:
    ema: bool = True
    pivots: bool = True
    levels: bool = True
    trendlines: bool = True
    fibonacci: bool = False
    formations: bool = True
    candles: bool = True


class ChartWidget(pg.GraphicsLayoutWidget):
    barHovered = QtCore.Signal(int)  # noqa: N815

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.price_axis = TimeAxis(orientation="bottom")
        self.volume_axis = TimeAxis(orientation="bottom")
        self.price = self.addPlot(row=0, col=0, axisItems={"bottom": self.price_axis})
        self.volume = self.addPlot(row=1, col=0, axisItems={"bottom": self.volume_axis})
        self.ci.layout.setRowStretchFactor(0, 5)
        self.ci.layout.setRowStretchFactor(1, 1)
        self.volume.setXLink(self.price)
        self.price.getAxis("bottom").setStyle(showValues=False)
        for plot in (self.price, self.volume):
            plot.showGrid(x=True, y=True, alpha=0.15)
            plot.setMenuEnabled(False)
            plot.hideButtons()
            plot.showAxis("right")
            plot.hideAxis("left")
        self.price.vb.setAutoVisible(y=True)
        self.volume.vb.setAutoVisible(y=True)
        self.price.vb.setMouseEnabled(x=True, y=False)
        self.volume.vb.setMouseEnabled(x=True, y=False)

        self.candles = CandlestickItem()
        self.price.addItem(self.candles)
        self.info = pg.TextItem(anchor=(0, 0), color=TEXT)
        self.info.setParentItem(self.price.vb)
        self.info.setPos(4, 2)
        self.vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#787b86", style=QtCore.Qt.DashLine))
        self.hline = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#787b86", style=QtCore.Qt.DashLine))
        self.price.addItem(self.vline, ignoreBounds=True)
        self.price.addItem(self.hline, ignoreBounds=True)
        self._mouse_proxy = pg.SignalProxy(self.price.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse)

        self.result: AnalysisResult | None = None
        self.offset = 0
        self.view: pd.DataFrame | None = None
        self.overlays = Overlays()
        self.selected: Formation | None = None
        self._overlay_items: list = []

    # ------------------------------------------------------------ veri

    def set_result(self, result: AnalysisResult, bars: int, keep_view: bool = False) -> None:
        old_range = self.price.vb.viewRange()[0] if keep_view and self.view is not None else None
        old_offset = self.offset
        self.result = result
        n = len(result.frame)
        self.offset = max(0, n - bars)
        self.view = result.frame.iloc[self.offset :]
        self.price_axis.times = self.volume_axis.times = self.view.index
        self.price_axis.daily = self.volume_axis.daily = result.interval == "1d"
        self.candles.set_data(self.view[["open", "high", "low", "close"]].to_numpy())
        self._draw_volume()
        self.redraw_overlays()
        if old_range is not None:
            shift = old_offset - self.offset
            self.price.setXRange(old_range[0] + shift, old_range[1] + shift, padding=0)
        else:
            m = len(self.view)
            # Sağda etiketler (olası hedef, seviyeler) için boşluk bırakılır.
            self.price.setXRange(max(0, m - 180), m + 30, padding=0)

    def _draw_volume(self) -> None:
        self.volume.clear()
        v = self.view
        rising = (v["close"] >= v["open"]).to_numpy()
        brushes = [pg.mkBrush(UP + "99") if r else pg.mkBrush(DOWN + "99") for r in rising]
        x = np.arange(len(v))
        self.volume.addItem(pg.BarGraphItem(x=x, height=v["volume"].to_numpy(), width=0.7, brushes=brushes, pens=[None] * len(v)))

    def x(self, index: int | np.ndarray) -> int | np.ndarray:
        """Analiz indeksini grafik x koordinatına çevirir."""
        return index - self.offset

    # ------------------------------------------------------------ katmanlar

    def _add(self, item, ignore_bounds: bool = True) -> None:
        self.price.addItem(item, ignoreBounds=ignore_bounds)
        self._overlay_items.append(item)

    def redraw_overlays(self) -> None:
        for item in self._overlay_items:
            self.price.removeItem(item)
        self._overlay_items = []
        if self.result is None or self.view is None:
            return
        o = self.overlays
        if o.ema:
            self._draw_emas()
        if o.pivots:
            self._draw_pivots()
        if o.levels:
            self._draw_levels()
        if o.trendlines:
            self._draw_trendlines()
        if o.fibonacci:
            self._draw_fibonacci()
        if o.candles:
            self._draw_candle_markers()
        if o.formations:
            self._draw_formations()
        elif self.selected is not None:
            self._draw_formation(self.selected, highlight=True)

    def _draw_emas(self) -> None:
        x = np.arange(len(self.view))
        for col, color in EMA_COLORS.items():
            self._add(pg.PlotDataItem(x, self.view[col].to_numpy(), pen=pg.mkPen(color, width=1), connect="finite"))

    def _draw_pivots(self) -> None:
        zz = self.result.zigzags[self.result.config.level_scale]
        pts = [p for p in zz.pivots if p.index >= self.offset]
        if pts:
            xs = np.array([self.x(p.index) for p in pts])
            ys = np.array([p.price for p in pts])
            self._add(pg.PlotDataItem(xs, ys, pen=pg.mkPen(PIVOT, width=1)))
            if zz.provisional is not None and zz.provisional.index >= self.offset:
                last = pts[-1]
                self._add(
                    pg.PlotDataItem(
                        [self.x(last.index), self.x(zz.provisional.index)],
                        [last.price, zz.provisional.price],
                        pen=pg.mkPen(PIVOT, width=1, style=QtCore.Qt.DotLine),
                    )
                )

    def _hline(
        self,
        x0: float,
        x1: float,
        y: float,
        color: str,
        style=QtCore.Qt.DashLine,
        width: float = 1.0,
        label: str | None = None,
        label_at_start: bool = False,
        in_bounds: bool = False,
    ) -> None:
        """Yatay çizgi. `in_bounds` ise dikey ölçek çizgiyi de kapsayacak şekilde ayarlanır."""
        self._add(pg.PlotDataItem([x0, x1], [y, y], pen=pg.mkPen(color, width=width, style=style)), ignore_bounds=not in_bounds)
        if label:
            # Seviye etiketleri çizginin sonunda sola dönük (sağ kenarda kesilmez);
            # hedef/stop etiketleri kırılım noktasında sağa dönük durur.
            text = pg.TextItem(label, color=color, anchor=(0, 1) if label_at_start else (1, 1))
            text.setPos(x0 if label_at_start else x1, y)
            self._add(text)

    def _draw_levels(self) -> None:
        end = len(self.view) + 5
        for lv in self.result.levels:
            color = LEVEL_SUPPORT if lv.kind == "destek" else LEVEL_RESIST
            start = max(0, self.x(lv.first_index))
            self._hline(start, end, lv.price, color, label=f"{lv.kind} {fmt_price(lv.price)} ({lv.touches})")

    def _draw_trendlines(self) -> None:
        end = len(self.view) - 1 + 5
        for tl in self.result.trendlines:
            color = LEVEL_SUPPORT if tl.kind == "destek" else LEVEL_RESIST
            x0 = max(self.x(tl.i1), 0)
            i0 = x0 + self.offset
            self._add(
                pg.PlotDataItem(
                    [x0, end], [tl.value_at(i0), tl.value_at(end + self.offset)], pen=pg.mkPen(color, width=1.5)
                )
            )

    def _draw_fibonacci(self) -> None:
        fib = self.result.fib
        if fib is None or fib.end_index < self.offset:
            return
        x0 = max(0, self.x(fib.start_index))
        x1 = len(self.view) + 5
        for ratio, value in fib.levels.items():
            self._hline(x0, x1, value, FIB, style=QtCore.Qt.DotLine, label=f"{ratio:g}".replace(".", ","))

    def _draw_candle_markers(self) -> None:
        events = self.result.candle_events(self.offset)
        if not events:
            return
        spots = []
        for e in events:
            x = self.x(e.index)
            row = self.view.iloc[x]
            if e.spec.bias > 0:
                spots.append({"pos": (x, row["low"]), "symbol": "t1", "brush": UP, "data": e.spec.name})
            elif e.spec.bias < 0:
                spots.append({"pos": (x, row["high"]), "symbol": "t", "brush": DOWN, "data": e.spec.name})
            else:
                spots.append({"pos": (x, row["high"]), "symbol": "o", "brush": "#787b86", "data": e.spec.name, "size": 5})
        scatter = pg.ScatterPlotItem(
            size=8,
            pen=None,
            hoverable=True,
            tip=lambda x, y, data: str(data),
            pxMode=True,
        )
        scatter.addPoints(spots)
        self._add(scatter)

    def _visible_formation(self, f: Formation) -> bool:
        t = self.result.as_of
        status = f.status_at(t)
        return f.end_index >= self.offset and (status in (FORMING, BROKEN) or status in RESOLVED)

    def _draw_formations(self) -> None:
        """Aktif formasyonlar tam, sonuçlanmışlar soluk ve etiketsiz çizilir; seçilen vurgulanır."""
        t = self.result.as_of
        for f in self.result.formations:
            if f is self.selected or not self._visible_formation(f):
                continue
            self._draw_formation(f, highlight=False, faint=f.status_at(t) in RESOLVED)
        if self.selected is not None:
            self._draw_formation(self.selected, highlight=True)

    def _draw_formation(self, f: Formation, highlight: bool, faint: bool = False) -> None:
        if f.end_index < self.offset:
            return
        t = self.result.as_of
        color = direction_color(f.direction if f.direction else f.bias)
        if faint:
            xs = np.array([self.x(i) for i, _ in f.points])
            ys = np.array([p for _, p in f.points])
            self._add(pg.PlotDataItem(xs, ys, pen=pg.mkPen(color + "55", width=1)))
            return
        width = 2.5 if highlight else 1.2
        xs = np.array([self.x(i) for i, _ in f.points])
        ys = np.array([p for _, p in f.points])
        self._add(pg.PlotDataItem(xs, ys, pen=pg.mkPen(color, width=width)))

        stop_at = f.breakout_index if f.breakout_index is not None else min(f.expiry_index, t)
        for line in (f.upper, f.lower):
            if line is None:
                continue
            a, b = f.start_index, max(stop_at, f.end_index)
            self._add(
                pg.PlotDataItem(
                    [self.x(a), self.x(b)],
                    [float(line.at(a)), float(line.at(b))],
                    pen=pg.mkPen(color, width=width * 0.8, style=QtCore.Qt.DashLine),
                )
            )

        status = f.status_at(t)
        if f.breakout_index is not None and f.target is not None and f.stop is not None:
            x0 = self.x(f.breakout_index)
            x1 = self.x(min(f.breakout_index + f.outcome_bars, t + 10))
            show = highlight or status == BROKEN
            self._hline(x0, x1, f.target, UP if f.direction > 0 else DOWN, style=QtCore.Qt.DotLine, width=width * 0.8,
                        label=f"hedef {fmt_price(f.target)}" if show else None, label_at_start=True, in_bounds=highlight)
            self._hline(x0, x1, f.stop, "#9e9e9e", style=QtCore.Qt.DotLine, width=width * 0.8,
                        label=f"stop {fmt_price(f.stop)}" if show else None, label_at_start=True, in_bounds=highlight)
        elif status == FORMING:
            for d, lv in f.pending_levels(t).items():
                x0, x1 = self.x(t), self.x(t) + 15
                self._hline(x0, x1, lv["target"], UP if d > 0 else DOWN, style=QtCore.Qt.DotLine, width=width * 0.8,
                            label=f"olası hedef {fmt_price(lv['target'])}", label_at_start=True, in_bounds=highlight)

        top = max(p for _, p in f.points) if f.bias <= 0 else min(p for _, p in f.points)
        label = pg.TextItem(f"{f.name} · {status}", color=color, anchor=(0.5, 1.2 if f.bias <= 0 else -0.2))
        label.setPos(float(xs.mean()), top)
        self._add(label)

    # ------------------------------------------------------------ etkileşim

    def focus(self, f: Formation) -> None:
        self.selected = f
        self.redraw_overlays()
        end = f.outcome_index or f.breakout_index or f.end_index
        a, b = self.x(f.start_index), self.x(end)
        pad = max(10, (b - a) // 2)
        self.price.setXRange(a - pad, b + pad, padding=0)

    def _on_mouse(self, event) -> None:
        if self.view is None:
            return
        pos = event[0]
        if not self.price.sceneBoundingRect().contains(pos):
            return
        point = self.price.vb.mapSceneToView(pos)
        i = int(round(point.x()))
        if not 0 <= i < len(self.view):
            return
        self.vline.setPos(i)
        self.hline.setPos(point.y())
        row = self.view.iloc[i]
        stamp = self.view.index[i].strftime("%Y-%m-%d %H:%M")
        change = f"{(row['close'] / row['open'] - 1) * 100:+.2f}".replace(".", ",")
        self.info.setText(
            f"{stamp} UTC   A {fmt_price(row['open'])}  Y {fmt_price(row['high'])}  "
            f"D {fmt_price(row['low'])}  K {fmt_price(row['close'])}  (%{change})"
        )
        self.barHovered.emit(i + self.offset)
