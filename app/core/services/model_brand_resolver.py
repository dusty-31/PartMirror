from dataclasses import dataclass
from typing import Optional
import re


@dataclass(frozen=True)
class _TripRef:
    trip: dict
    brands_lower: set[str]


class ModelBrandResolver:
    def __init__(self, triplets_raw: list[dict]) -> None:
        self._full_map: dict[str, list[_TripRef]] = {}
        self._base_map: dict[str, list[_TripRef]] = {}

        def norm(s: str) -> str:
            return " ".join(str(s).strip().lower().split())

        def base_token(model: str) -> Optional[str]:

            tokens = [token for token in re.split(r"[\s.\-_/]+", model) if token]
            if not tokens:
                return None
            b = tokens[0]
            if len(b) < 2 and not any(ch.isdigit() for ch in b):
                return None
            return b.lower()

        for t in triplets_raw:
            brands = {t["ua"]["brand"].lower(), t["ru"]["brand"].lower(), t["en"]["brand"].lower()}
            ref = _TripRef(trip=t, brands_lower=brands)

            for lang in ("ua", "ru", "en"):
                m = t[lang]["model"]
                if not m:
                    continue
                key = norm(m)
                self._full_map.setdefault(key, []).append(ref)

                b = base_token(m)
                if b:
                    self._base_map.setdefault(b, []).append(ref)

    def resolve(self, model_str: str, prefer_brand: Optional[str] = None) -> Optional[dict]:
        """
        Resolve the model string to a triplet dictionary.
        """
        if model_str is None:
            return None

        def pick(candidates: list[_TripRef]) -> Optional[dict]:
            if not candidates:
                return None
            if prefer_brand:
                pb = prefer_brand.strip().lower()
                for ref in candidates:
                    if pb in ref.brands_lower:
                        return ref.trip
            return candidates[0].trip

        key_full = " ".join(str(model_str).strip().lower().split())
        trip = pick(self._full_map.get(key_full, []))
        if trip:
            return trip

        tokens = [t for t in re.split(r"[\s.\-_/]+", key_full) if t]
        base = tokens[0] if tokens else None
        if base:
            return pick(self._base_map.get(base, []))

        return None
