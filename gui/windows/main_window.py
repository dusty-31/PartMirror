import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from gui.logging_handlers import QtLogHandler
from gui.worker import Worker
from gui.models.dataframe_model import DataFrameModel
import pandas as pd
from gui.styles import BASE_STYLESHEET, MARGINS, SPACING_MEDIUM, SPACING_SMALL, system_mono_font
from gui.config import APP_ORG, APP_NAME

# identifiers come from gui.config


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, process_excel_callable) -> None:
        super().__init__()
        self._process_excel = process_excel_callable

        self.setWindowTitle(f"{APP_ORG} - {APP_NAME}")
        self.resize(960, 640)

        self._selected_path: Optional[Path] = None
        self._worker: Optional[Worker] = None
        self._start_time_ms: Optional[int] = None
        self._settings = QtCore.QSettings(APP_ORG, APP_NAME)

        # Layout: top toolbar row + splitter (preview | logs) + progress + status
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        # Set margins explicitly to satisfy IDE overload resolution
        root.setContentsMargins(MARGINS[0], MARGINS[1], MARGINS[2], MARGINS[3])
        root.setSpacing(SPACING_MEDIUM)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(SPACING_SMALL)
        root.addLayout(toolbar)

        self.btn_choose = QtWidgets.QPushButton("Choose file…")
        self.btn_choose.setShortcut(QtGui.QKeySequence(
            "Ctrl+O" if sys.platform.startswith("win") or sys.platform.startswith("linux") else "Meta+O"))
        self.btn_choose.clicked.connect(self.on_choose_file)
        toolbar.addWidget(self.btn_choose)

        self.lbl_path = QtWidgets.QLabel("No file selected")
        self.lbl_path.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.lbl_path.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        toolbar.addWidget(self.lbl_path, 1)

        self.btn_process = QtWidgets.QPushButton("Process")
        self.btn_process.setProperty("primary", True)
        self.btn_process.setDefault(True)
        self.btn_process.setEnabled(False)
        self.btn_process.setShortcut(QtGui.QKeySequence(
            "Ctrl+R" if sys.platform.startswith("win") or sys.platform.startswith("linux") else "Meta+R"))
        self.btn_process.clicked.connect(self.on_start_processing)
        toolbar.addWidget(self.btn_process)

        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setShortcut(QtGui.QKeySequence(
            "Ctrl+." if sys.platform.startswith("win") or sys.platform.startswith("linux") else "Meta+."))
        self.btn_cancel.clicked.connect(self.on_cancel)
        toolbar.addWidget(self.btn_cancel)

        # Splitter area (logs sidebar resizable)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        root.addWidget(self.splitter, 1)

        # Left: preview only (white drop area removed)
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SPACING_SMALL)

        # Preview table (shows first N rows after processing)
        self.preview_model = DataFrameModel()
        self.preview = QtWidgets.QTableView()
        self.preview.setModel(self.preview_model)
        self.preview.setAlternatingRowColors(True)
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.preview.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        left_layout.addWidget(self.preview, 1)
        self.splitter.addWidget(left)

        # Right: logs
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(SPACING_SMALL)

        self.logs = QtWidgets.QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setFont(system_mono_font())
        self.logs.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.logs.customContextMenuRequested.connect(self._show_logs_context_menu)
        right_layout.addWidget(self.logs, 1)

        self.splitter.addWidget(right)
        saved = self._settings.value("splitter_sizes")
        if isinstance(saved, list) and all(isinstance(x, int) for x in saved):
            self.splitter.setSizes([int(x) for x in saved])
        else:
            self.splitter.setSizes([640, 320])

        # Progress bar
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # Status bar
        self.status = self.statusBar()
        # Toggle sidebar action
        self._act_toggle_logs = QtGui.QAction("Toggle Logs", self)
        self._act_toggle_logs.triggered.connect(self._toggle_logs_sidebar)
        self.addAction(self._act_toggle_logs)

        # Shortcuts
        quit_sc = QtGui.QShortcut(
            QtGui.QKeySequence(
                "Ctrl+Q" if sys.platform.startswith("win") or sys.platform.startswith("linux") else "Meta+Q"),
            self,
        )
        quit_sc.activated.connect(self.close)

        # Logging to UI
        self._logger = logging.getLogger("gui")
        self._logger.setLevel(logging.INFO)
        self._qt_handler = QtLogHandler()
        self._qt_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self._qt_handler.sig_message.connect(self._append_log_line)
        logging.getLogger().addHandler(self._qt_handler)

        # Stylesheet
        self.setStyleSheet(BASE_STYLESHEET)

    # ---------------- UI helpers ----------------
    def _show_logs_context_menu(self, pos: QtCore.QPoint) -> None:
        menu = self.logs.createStandardContextMenu()
        menu.addSeparator()
        action_copy_all = menu.addAction("Copy logs")
        action_copy_all.triggered.connect(lambda: QtWidgets.QApplication.clipboard().setText(self.logs.toPlainText()))
        menu.exec(self.logs.mapToGlobal(pos))

    def _append_log_line(self, line: str) -> None:
        self.logs.appendPlainText(line)
        cursor = self.logs.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        self.logs.setTextCursor(cursor)

    def _update_path_label(self) -> None:
        if not self._selected_path:
            self.lbl_path.setText("No file selected")
            return
        metrics = self.lbl_path.fontMetrics()
        elided = metrics.elidedText(str(self._selected_path), QtCore.Qt.TextElideMode.ElideMiddle,
                                    self.lbl_path.width())
        self.lbl_path.setText(elided)

    # ---------------- Events ----------------
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_path_label()

    def on_choose_file(self) -> None:
        start_dir = str(self._settings.value("last_dir", str(Path.home())))
        file_path, _filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Choose Excel file",
            start_dir,
            "Excel Files (*.xlsx)"
        )
        if file_path:
            self._settings.setValue("last_dir", str(Path(file_path).parent))
            self._set_selected_file(Path(file_path))

    def _set_selected_file(self, path: Path) -> None:
        if not path.exists() or path.suffix.lower() != ".xlsx":
            QtWidgets.QMessageBox.warning(self, "Invalid file", "Please choose a valid .xlsx file.")
            return
        self._selected_path = path
        self._update_path_label()
        self.btn_process.setEnabled(True)
        self.logs.appendPlainText(f"Selected file: {path}")

    def on_start_processing(self) -> None:
        if not self._selected_path:
            return
        self.logs.clear()
        self.progress.setVisible(True)
        self.btn_process.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self._start_time_ms = QtCore.QTime.currentTime().msecsSinceStartOfDay()

        worker_logger = logging.getLogger("pipeline")
        worker_logger.setLevel(logging.INFO)

        self._worker = Worker(self._selected_path, worker_logger, self._process_excel, parent=self)
        self._worker.finished_ok.connect(self._on_worker_success)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.logs.appendPlainText("Cancellation requested…")

    def _on_worker_success(self, output_path: Path) -> None:
        self.logs.appendPlainText(f"Processing finished. Temporary output: {output_path}")
        # Try to load a small preview from the output file
        try:
            df = pd.read_excel(str(output_path))
        except (OSError, ValueError) as exc:
            logging.getLogger().error("Failed to load preview from output: %s", exc)
        else:
            self.preview_model.set_dataframe(df.head(200))
        suggested = output_path.name
        start_dir = str(self._settings.value("last_dir", str(Path.home())))
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save As",
            str(Path(start_dir) / suggested),
            "Excel Files (*.xlsx)"
        )
        if save_path:
            try:
                if Path(save_path).resolve() == Path(output_path).resolve():
                    self.logs.appendPlainText("Destination is the same as the temporary file. Skipping copy.")
                    return
                shutil.copyfile(str(output_path), save_path)
            except OSError as exc:
                logging.getLogger().error("Failed to save output file: %s", exc)
                QtWidgets.QMessageBox.critical(self, "Save Error", str(exc))
            else:
                self.logs.appendPlainText(f"Saved to: {save_path}")
                self._settings.setValue("last_dir", str(Path(save_path).parent))
        else:
            self.logs.appendPlainText("Save canceled. Temporary file remains at: " + str(output_path))

    def _on_worker_failed(self, message: str) -> None:
        self.logs.appendPlainText("ERROR: " + message)
        QtWidgets.QMessageBox.critical(self, "Processing Error", message)

    def _on_worker_finished(self) -> None:
        self.progress.setVisible(False)
        self.btn_cancel.setEnabled(False)
        self.btn_process.setEnabled(self._selected_path is not None)
        if self._start_time_ms is not None:
            elapsed_ms = QtCore.QTime.currentTime().msecsSinceStartOfDay() - self._start_time_ms
            self.status.showMessage(f"Done in {elapsed_ms / 1000:.2f}s")
        self._worker = None
        self._settings.setValue("splitter_sizes", self.splitter.sizes())

    # Sidebar toggle
    def _toggle_logs_sidebar(self) -> None:
        sizes = self.splitter.sizes()
        if sizes[1] > 0:
            self._settings.setValue("splitter_prev", sizes[1])
            self.splitter.setSizes([sum(sizes), 0])
        else:
            prev_value = self._settings.value("splitter_prev", 320)
            try:
                prev = int(prev_value)  # type: ignore[assignment]
            except (TypeError, ValueError):
                prev = 320
            self.splitter.setSizes([max(200, sum(sizes) - prev), prev])

    # Drag & drop support (window-wide)
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        if self._has_valid_xlsx(event):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:  # type: ignore[override]
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            path = Path(urls[0].toLocalFile())
            if path.exists() and path.suffix.lower() == ".xlsx":
                self._set_selected_file(path)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    @staticmethod
    def _has_valid_xlsx(event: QtGui.QDragEnterEvent) -> bool:
        md = event.mimeData()
        if not md.hasUrls():
            return False
        urls = md.urls()
        if len(urls) != 1:
            return False
        url = urls[0]
        if not url.isLocalFile():
            return False
        path = Path(url.toLocalFile())
        return path.exists() and path.suffix.lower() == ".xlsx"
