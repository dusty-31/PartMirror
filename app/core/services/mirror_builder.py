import pandas as pd

from app.core.dataclasses import TripIndex
from app.core.services.row_transformer import RowTransformer
from app.core.services.compat_utils import dedupe_models, same_pair, clear_fields
from app.core.services.model_brand_resolver import ModelBrandResolver
from app.config import MIRROR_CLEAR_COLUMNS


class MirrorBuilder:
    """
    Creates mirror rows based on the original row and compatibility map.
    Like "Original" + 0..N "Mirror" rows.
    """

    def __init__(self, transformer: RowTransformer, trip_index: TripIndex, resolver: ModelBrandResolver) -> None:
        self._transformer = transformer
        self._trip_index = trip_index
        self._resolver = resolver

    def build_rows_for(self, row: pd.Series) -> list[pd.Series]:
        result: list[pd.Series] = []

        current_brand = row.get("Марка", "")
        current_model = row.get("Модель", "")
        raw_compat = row.get("Совместимость", "")

        # Original row
        orig_row = row.copy()
        orig_row["Тип_записи"] = "Оригінал"
        orig_row = self._transformer.apply_all(
            orig_row,
            src_brand=current_brand,
            src_model=current_model,
            dst_pair=None,
        )
        result.append(orig_row)

        # Creating mirrors rows
        for model in dedupe_models(raw_compat):
            dst_trip = self._resolver.resolve(model)
            if not dst_trip:
                continue

            dst_brand = dst_trip["en"]["brand"]
            dst_model = dst_trip["en"]["model"]

            if same_pair(dst_brand, dst_model, current_brand, current_model):
                continue

            new_row = row.copy()
            new_row["Марка"] = dst_brand
            new_row["Модель"] = dst_model
            if "Категория_BAS" in new_row:
                new_row["Категория_BAS"] = dst_model

            new_row["Тип_записи"] = "Дзеркало"
            if "Артикул" in new_row:
                new_row["Новый_артикул"] = new_row.get("Артикул")
                new_row["Артикул"] = pd.NA

            new_row = clear_fields(new_row, MIRROR_CLEAR_COLUMNS)
            new_row = self._transformer.apply_all(
                new_row,
                src_brand=current_brand,
                src_model=current_model,
                dst_pair=dst_trip,
            )
            result.append(new_row)

        return result
