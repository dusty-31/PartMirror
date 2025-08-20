from typing import Protocol
from app.core.dataclasses import TripIndex, Triplets


class TripDataProvider(Protocol):
    def load_triplets(self) -> Triplets:
        """Load triplets data."""
        pass

    def build_index(self, triplets: Triplets) -> TripIndex:
        """Build an index from triplets data."""
        pass
