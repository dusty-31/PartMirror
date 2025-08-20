import json

from app.gateways.compatibility_provider import CompatibilityProvider
from app.core.dataclasses import CompatibilityMap


class JsonCompatibilityProvider(CompatibilityProvider):
    def __init__(self, path: str) -> None:
        self._path = path

    def load(self) -> CompatibilityMap:
        """Load compatibility data from a JSON file."""
        with open(self._path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return CompatibilityMap(raw=data)
