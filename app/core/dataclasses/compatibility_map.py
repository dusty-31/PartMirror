from dataclasses import dataclass


@dataclass(frozen=True)
class CompatibilityMap:
    raw: dict[str, list[str]]

    def find_brand_by_model(self, model: str | None) -> str | None:
        if model is None:
            return None
        normalized_model = str(model).strip().lower()
        for brand, models in self.raw.items():
            for model_from_map in (models or []):
                if str(model_from_map).strip().lower() == normalized_model:
                    return brand
        return None
