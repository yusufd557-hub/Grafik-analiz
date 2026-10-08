"""Masaüstü uygulamasının ekransız (offscreen) duman testi."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from grafik_analiz.analysis import AnalysisConfig, analyze  # noqa: E402

from .synthetic import random_walk  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_window_shows_analysis(app):
    from grafik_analiz.app.window import MainWindow

    result = analyze(random_walk(2000), "BTCUSDT", "1h", AnalysisConfig(max_bars=None))
    window = MainWindow()
    window.show_result(result)
    assert "BTCUSDT" in window.summary.toPlainText()
    assert window.stats_table.rowCount() == len(result.formation_stats)

    window.formation_filter.setCurrentText("Hepsi")
    assert window.formation_table.rowCount() > 0
    window.formation_table.selectRow(0)
    assert window.chart.selected is not None

    for box in window.overlay_boxes.values():
        box.setChecked(not box.isChecked())
    window.bars_box.setValue(500)
    window._redisplay()
    window.close()
