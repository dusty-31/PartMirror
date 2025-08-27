import logging
import traceback
from pathlib import Path
from typing import Optional, Callable

from PySide6 import QtCore


class Worker(QtCore.QThread):
    """Background worker that runs the Excel processing pipeline.

    Signals:
        finished_ok(Path): Processing finished successfully, provides output path.
        failed(str): Processing failed, provides error message/trace.
        progressed(int): Optional progress updates (0-100). Not used for now.
    """

    finished_ok = QtCore.Signal(Path)
    failed = QtCore.Signal(str)
    progressed = QtCore.Signal(int)

    def __init__(
            self,
            input_path: Path,
            logger: logging.Logger,
            processor: Callable[[Path, logging.Logger], Path],
            parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._input_path = input_path
        self._logger = logger
        self._processor = processor
        self._cancel_requested = False

    def cancel(self) -> None:
        """Request cancellation. Pipeline may choose to check a flag.

        If the underlying pipeline does not support cooperative cancellation,
        the UI will still reflect that cancellation was requested.
        """
        self._cancel_requested = True
        # If your pipeline supports it, you can pass this flag via the logger or a context.

    def run(self) -> None:  # type: ignore[override]
        try:
            if self._cancel_requested:
                self._logger.info("Cancelled before start.")
                self.failed.emit("Cancelled")
                return

            self._logger.info(f"Starting processing: {self._input_path}")
            output = self._processor(self._input_path, self._logger)

            if self._cancel_requested:
                self._logger.info("Cancellation requested after processing.")
            self.finished_ok.emit(output)
        except (Exception,):
            trace = traceback.format_exc()
            try:
                self._logger.exception("Processing failed with an exception")
            finally:
                self.failed.emit(trace)
