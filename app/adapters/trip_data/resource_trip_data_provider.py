import json
from importlib.resources import files, as_file

from app.gateways.trip_data_prodiver import TripDataProvider
from app.core.dataclasses import TripIndex, Triplets
from app.utils.finder import build_trip_index
from app.config import ALLOWED_LANGUAGES


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
    BRANDS_JSON_PACKAGE = "adapters.trip_data.resources"

    def __init__(self, package: str = BRANDS_JSON_PACKAGE) -> None:
        self._package = package

    def _iter_brand_files(self):
        for entry in files(self._package).iterdir():
            if entry.is_file() and entry.name.endswith(".json"):
                yield entry

    @staticmethod
    def _collect_triplets(obj, out: list[dict]) -> None:
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
                ResourceTripDataProvider._collect_triplets(element, out)
            return
        if isinstance(obj, dict):
            for nested_value in obj.values():
                ResourceTripDataProvider._collect_triplets(nested_value, out)
            return

    def load_triplets(self) -> Triplets:
        items: list[dict] = []
        for result in self._iter_brand_files():
            with as_file(result) as path:
                print(f"Loading triplets from {path.name}...")
                data = json.loads(path.read_text(encoding="utf-8"))
            self._collect_triplets(data, items)
        return Triplets(raw=items)

    def build_index(self, triplets: Triplets) -> TripIndex:
        return TripIndex(raw=build_trip_index(triplets.raw))
