from dataclasses import dataclass
from typing import Optional
import re

from app.config import ALLOWED_LANGUAGES


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
            base_key = tokens[0]
            if len(base_key) < 2 and not any(ch.isdigit() for ch in base_key):
                return None
            return base_key.lower()

        for triplet in triplets_raw:
            brands = {triplet["ua"]["brand"].lower(), triplet["ru"]["brand"].lower(), triplet["en"]["brand"].lower()}
            ref = _TripRef(trip=triplet, brands_lower=brands)

            for lang in ALLOWED_LANGUAGES:
                model_value = triplet[lang]["model"]
                if not model_value:
                    continue
                key = norm(model_value)
                self._full_map.setdefault(key, []).append(ref)

                base_key = base_token(model_value)
                if base_key:
                    self._base_map.setdefault(base_key, []).append(ref)

    def resolve(self, model_str: str, prefer_brand: Optional[str] = None, *, allow_base_fallback: bool = True,) -> Optional[dict]:
        """
        Resolve the model string to a triplet dictionary.
        """
        if model_str is None:
            return None

        def pick(candidates: list[_TripRef]) -> Optional[dict]:
            if not candidates:
                return None
            if prefer_brand:
                pb_lower = prefer_brand.strip().lower()
                for ref in candidates:
                    if pb_lower in ref.brands_lower:
                        return ref.trip
            return candidates[0].trip

        key_full = " ".join(str(model_str).strip().lower().split())

        resolved = pick(self._full_map.get(key_full, []))
        if resolved or not allow_base_fallback:
            return resolved

        tokens = [token for token in re.split(r"[\s.\-_/]+", key_full) if token]
        base = tokens[0] if tokens else None
        if base:
            return pick(self._base_map.get(base, []))

        return None
