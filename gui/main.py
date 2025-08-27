from __future__ import annotations

"""
Entry point for the Excel Processor GUI.

Quick start:
    pip install PySide6
    python -m gui

Optional (macOS app bundle):
    pyinstaller --noconsole --name "Excel Processor" --windowed gui/main.py
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets

from gui.windows.main_window import MainWindow
from gui.config import APP_ORG, APP_NAME
from app.pipelines import ExcelFilePipeline


def process_excel(input_path: Path, logger: logging.Logger) -> Path:
    pipeline = ExcelFilePipeline()
    return pipeline.process_file(input_path, logger)


# Application identifiers configured via gui/config.py


def _configure_root_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def main(argv: Optional[list[str]] = None) -> int:
    _configure_root_logging()
    argv = argv if argv is not None else sys.argv

    QtCore.QCoreApplication.setOrganizationName(APP_ORG)
    QtCore.QCoreApplication.setApplicationName(APP_NAME)

    app = QtWidgets.QApplication(argv)
    app.setFont(QtGui.QFont())

    win = MainWindow(process_excel)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
