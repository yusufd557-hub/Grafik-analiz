"""Masaüstü uygulamasını başlatır: `python -m grafik_analiz.app`."""

from __future__ import annotations

import sys

from PySide6 import QtGui, QtWidgets


def dark_palette() -> QtGui.QPalette:
    palette = QtGui.QPalette()
    colors = {
        QtGui.QPalette.Window: "#1e222d",
        QtGui.QPalette.WindowText: "#d1d4dc",
        QtGui.QPalette.Base: "#131722",
        QtGui.QPalette.AlternateBase: "#1a1e29",
        QtGui.QPalette.ToolTipBase: "#2a2e39",
        QtGui.QPalette.ToolTipText: "#d1d4dc",
        QtGui.QPalette.Text: "#d1d4dc",
        QtGui.QPalette.Button: "#2a2e39",
        QtGui.QPalette.ButtonText: "#d1d4dc",
        QtGui.QPalette.Highlight: "#2962ff",
        QtGui.QPalette.HighlightedText: "#ffffff",
        QtGui.QPalette.PlaceholderText: "#787b86",
    }
    for role, color in colors.items():
        palette.setColor(role, QtGui.QColor(color))
    return palette


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Grafik Analiz")
    app.setStyle("Fusion")
    app.setPalette(dark_palette())

    from .window import MainWindow

    window = MainWindow()
    window.show()
    window.load(refresh=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
