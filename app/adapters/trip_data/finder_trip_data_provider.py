from app.gateways.trip_data_prodiver import TripDataProvider
from app.core.dataclasses import TripIndex, Triplets
from app.utils.finder import load_triplets, build_trip_index


class FinderTripDataProvider(TripDataProvider):
    """Reads a single cars.json file"""

    def __init__(self, path: str) -> None:
        self._path = path

    def load_triplets(self) -> Triplets:
        return Triplets(raw=load_triplets(self._path))

    def build_index(self, triplets: Triplets) -> TripIndex:
        return TripIndex(raw=build_trip_index(triplets.raw))
