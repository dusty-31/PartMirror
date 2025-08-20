import json
from importlib.resources import files, as_file

from app.gateways.trip_data_prodiver import TripDataProvider
from app.core.dataclasses import TripIndex, Triplets
from app.utils.finder import build_trip_index


class ResourceTripDataProvider(TripDataProvider):
    """
    Read all brands json from resource packages.
    """
    BRANDS_JSON_PACKAGE = "adapters.trip_data.resources"

    def __init__(self, package: str = BRANDS_JSON_PACKAGE) -> None:
        self._package = package

    def _iter_brand_files(self):
        print("current path", self._package)
        for p in files(self._package).iterdir():
            if p.name.endswith(".json"):
                yield p

    def load_triplets(self) -> Triplets:
        items: list[dict] = []

        for result in self._iter_brand_files():
            with as_file(result) as path:
                items.append(json.loads(path.read_text(encoding="utf-8")))
        return Triplets(raw=items)

    def build_index(self, triplets: Triplets) -> TripIndex:
        return TripIndex(raw=build_trip_index(triplets.raw))
