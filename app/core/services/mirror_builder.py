import pandas as pd

from app.core.dataclasses import TripIndex, CompatibilityMap
from app.core.services.row_transformer import RowTransformer
from app.core.services.compat_utils import dedupe_models, same_pair, clear_fields
from app.config import MIRROR_CLEAR_COLUMNS


class MirrorBuilder:
    """
    Creates mirror rows based on the original row and compatibility map.
    Like "Original" + 0..N "Mirror" rows.
    """

    def __init__(self, transformer: RowTransformer, trip_index: TripIndex) -> None:
        self._transformer = transformer
        self._trip_index = trip_index

    def build_rows_for(self, row: pd.Series, compat_map: CompatibilityMap) -> list[pd.Series]:
        result: list[pd.Series] = []

        current_brand = row.get("Марка", "")
        current_model = row.get("Модель", "")
        raw_compat = row.get("Совместимость", "")

        # 1) Original row
        orig_row = row.copy()
        orig_row["Тип_записи"] = "Оригінал"
        orig_row = self._transformer.apply_all(
            orig_row,
            src_brand=current_brand,
            src_model=current_model,
            dst_pair=None,
        )
        result.append(orig_row)

        # 2) Mirror rows
        for model in dedupe_models(raw_compat):
            brand = compat_map.find_brand_by_model(model)
            if not brand:
                continue
            if same_pair(brand, model, current_brand, current_model):
                continue

            dst_pair = self._trip_index.get_pair(brand, model)
            if not dst_pair:
                continue

            new_row = row.copy()
            new_row["Марка"] = brand
            new_row["Модель"] = model
            if "Категория_BAS" in new_row:
                new_row["Категория_BAS"] = model

            new_row["Тип_записи"] = "Дзеркало"
            if "Артикул" in new_row:
                new_row["Новый_артикул"] = new_row.get("Артикул")
                new_row["Артикул"] = pd.NA

            new_row = clear_fields(new_row, MIRROR_CLEAR_COLUMNS)

            new_row = self._transformer.apply_all(
                new_row,
                src_brand=current_brand,
                src_model=current_model,
                dst_pair=dst_pair,
            )
            result.append(new_row)

        return result
