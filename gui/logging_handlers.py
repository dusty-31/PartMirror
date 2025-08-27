import logging
from PySide6 import QtCore


class QtLogHandler(logging.Handler, QtCore.QObject):
    """A logging handler that emits log lines via a Qt signal.

    Subclasses both QObject and logging.Handler so that ``sig_message`` is a
    real Qt signal you can connect to.
    """

    sig_message = QtCore.Signal(str)

    def __init__(self) -> None:
        logging.Handler.__init__(self)
        QtCore.QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            msg = self.format(record)
        except (Exception,):
            msg = record.getMessage()
        self.sig_message.emit(msg)
