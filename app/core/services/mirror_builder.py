import pandas as pd

from app.core.dataclasses import TripIndex
from app.core.services.row_transformer import RowTransformer
from app.core.enums import ExcelColumns, CustomExcelColumns, RecordTypeChoices
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

        current_brand = row.get(ExcelColumns.BRAND.value, "")
        current_model = row.get(ExcelColumns.MODEL.value, "")
        raw_compat = row.get(ExcelColumns.COMPATIBILITY.value, "")

        # Original row
        orig_row = row.copy()
        orig_row[CustomExcelColumns.RECORD_TYPE.value] = RecordTypeChoices.ORIGINAL.value
        orig_row = self._transformer.apply_all(
            orig_row,
            src_brand=current_brand,
            src_model=current_model,
            dst_pair=None,
        )
        result.append(orig_row)

        # Creating mirrors rows
        for model in dedupe_models(raw_compat):
            resolved_triplet = self._resolver.resolve(model, allow_base_fallback=False)
            if not resolved_triplet:
                continue

            target_brand = resolved_triplet["en"]["brand"]
            target_model = resolved_triplet["en"]["model"]

            if same_pair(target_brand, target_model, current_brand, current_model):
                continue

            new_row = row.copy()
            new_row[ExcelColumns.BRAND.value] = target_brand
            new_row[ExcelColumns.MODEL.value] = target_model
            if ExcelColumns.BAS_CATEGORY.value in new_row:
                new_row[ExcelColumns.BAS_CATEGORY.value] = target_model

            new_row[CustomExcelColumns.RECORD_TYPE.value] = RecordTypeChoices.MIRROR.value
            if ExcelColumns.ARTICLE in new_row:
                new_row[ExcelColumns.NEW_ARTICLE.value] = new_row.get(ExcelColumns.ARTICLE.value)
                new_row[ExcelColumns.ARTICLE.value] = pd.NA

            new_row = clear_fields(new_row, MIRROR_CLEAR_COLUMNS)
            new_row = self._transformer.apply_all(
                new_row,
                src_brand=current_brand,
                src_model=current_model,
                dst_pair=resolved_triplet,
            )
            result.append(new_row)

        return result
