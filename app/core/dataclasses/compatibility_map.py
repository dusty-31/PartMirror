from dataclasses import dataclass


@dataclass(frozen=True)
class CompatibilityMap:
    raw: dict[str, list[str]]

    def find_brand_by_model(self, model: str | None) -> str | None:
        if model is None:
            return None
        m = str(model).strip().lower()
        for brand, models in self.raw.items():
            for mm in (models or []):
                if str(mm).strip().lower() == m:
                    return brand
        return None
