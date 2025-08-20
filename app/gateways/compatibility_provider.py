from typing import Protocol

from app.core.dataclasses import CompatibilityMap


class CompatibilityProvider(Protocol):
    def load(self) -> CompatibilityMap:
        """Load compatibility data."""
        pass
