"""Application entry point."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from .ui.window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setOrganizationName("FinancialOdyssey")
    app.setApplicationName("Financial Odyssey")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
