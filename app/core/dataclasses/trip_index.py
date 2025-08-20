from dataclasses import dataclass


@dataclass(frozen=True)
class TripIndex:
    raw: dict

    def get_pair(self, brand: str, model: str) -> dict | None:
        key = (str(brand).lower(), str(model).lower())
        return self.raw.get(key)
