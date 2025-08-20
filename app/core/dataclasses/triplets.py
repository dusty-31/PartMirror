from dataclasses import dataclass


@dataclass(frozen=True)
class Triplets:
    """Dataclass of original triplets data."""
    raw: list[dict]
