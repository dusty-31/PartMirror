import json
import logging
from pathlib import Path
from typing import Optional, Iterator

import app.adapters.trip_data.resources as trip_resources

from app.gateways.trip_data_prodiver import TripDataProvider
from app.core.dataclasses import TripIndex, Triplets
from app.utils.finder import build_trip_index
from app.settings import ALLOWED_LANGUAGES

logger = logging.getLogger(__name__)


def _is_triplet_dict(obj: dict) -> bool:
    """
    Check if the object is a triplet dictionary.
    """
    if not type(obj) is dict:
        return False
    for language in ALLOWED_LANGUAGES:
        language_entry = obj.get(language)
        if not type(language_entry) is dict or "brand" not in language_entry or "model" not in language_entry:
            return False
    return True


class ResourceTripDataProvider(TripDataProvider):
    """
    Read all brands json from resource packages.
    """

    def __init__(self, base_dir: Optional[Path | str] = None):
        if base_dir is None:
            package_file = getattr(trip_resources, "__file__", None)
            if package_file is None:
                raise RuntimeError(
                    f"Cannot resolve resource package path: {trip_resources} has no __file__ attribute"
                )
            self._base_dir = Path(package_file).resolve().parent
        else:
            self._base_dir = Path(base_dir).resolve()

        if not self._base_dir.is_dir():
            raise NotADirectoryError(f"Base directory does not exist: {self._base_dir}")

    def _iter_brand_files(self) -> Iterator[Path]:
        """
        Iterate *.json files in the base directory.
        """
        yield from sorted(self._base_dir.glob("*.json"))

    @classmethod
    def _collect_triplets(cls, obj, out: list[dict]) -> None:
        """
        Collect triplets from the object.
        """
        if obj is None:
            return
        if _is_triplet_dict(obj):
            out.append(obj)
            return
        if isinstance(obj, list):
            for element in obj:
                cls._collect_triplets(element, out)
            return
        if isinstance(obj, dict):
            for nested_value in obj.values():
                cls._collect_triplets(nested_value, out)
            return

    def load_triplets(self) -> Triplets:
        items: list[dict] = []
        for path in self._iter_brand_files():
            logger.info(f"Loading triplets from: {path.name}... ")
            data = json.loads(path.read_text(encoding="utf-8"))
            self._collect_triplets(data, items)
        return Triplets(raw=items)

    def build_index(self, triplets: Triplets) -> TripIndex:
        return TripIndex(raw=build_trip_index(triplets.raw))
