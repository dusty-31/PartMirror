import time
import logging
from typing import Type, Optional
from types import TracebackType

logger = logging.getLogger(__name__)


class Timer:
    """
    Context manager for timing code execution.
    """

    def __init__(self, label: str) -> None:
        self.label = label
        self.start_time: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        logger.info("[START] %s", self.label)
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_value: Optional[BaseException],
            traceback: Optional[TracebackType],
    ) -> None:
        elapsed = time.perf_counter() - self.start_time
        if exc_type:
            logger.error(f"[FAIL ] {self.label} — {elapsed:.2f}s")
        else:
            logger.info(f"[DONE ] {self.label} — {time.perf_counter() - self.start_time:.2f}s")
