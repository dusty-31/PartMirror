from typing import Optional

import pandas as pd

from app.core.dataclasses import TripIndex
from app.core.services.row_transformer import RowTransformer
from app.core.enums import ExcelColumns, CustomExcelColumns, RecordTypeChoices
from app.core.services.compat_utils import dedupe_models, same_pair, clear_fields
from app.core.services.model_brand_resolver import ModelBrandResolver
from app.settings import MIRROR_CLEAR_COLUMNS


class MirrorBuilder:
    """
    Creates mirror rows based on the original row and compatibility map.
    Like "Original" + 0..N "Mirror" rows.
    """

    def __init__(
            self,
            transformer: RowTransformer,
            trip_index: TripIndex,
            resolver: ModelBrandResolver,
            include_record_type: bool = False,
            filtered_groups: Optional[dict[str, str]] = None,
    ) -> None:
        self._transformer = transformer
        self._trip_index = trip_index
        self._resolver = resolver
        self._include_record_type = include_record_type
        self._filtered_groups: dict[str, str] = filtered_groups or {}

    def set_include_record_type(self, include: bool) -> None:
        """
        Enable or disable the RECORD_TYPE column in the output.
        
        Args:
            include: If True, adds RECORD_TYPE column to distinguish original vs mirror rows
        """
        self._include_record_type = include

    def build_rows_for(self, row: pd.Series) -> list[pd.Series]:
        result: list[pd.Series] = []

        current_brand = row.get(ExcelColumns.BRAND.value, "")
        current_model = row.get(ExcelColumns.MODEL.value, "")
        raw_compat = row.get(ExcelColumns.COMPATIBILITY.value, "")

        # Original row
        orig_row = row.copy()
        if self._include_record_type:
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

            target_brand, target_model = resolved_triplet["en"].values()
            target_brand_ua, target_model_ua = resolved_triplet["ua"].values()
            target_brand_ru, target_model_ru = resolved_triplet["ru"].values()

            if same_pair(target_brand, target_model, current_brand, current_model):
                continue

            new_row = row.copy()
            # Update brand/model in all languages
            # English
            new_row[ExcelColumns.BRAND.value] = target_brand
            new_row[ExcelColumns.MODEL.value] = target_model
            # Russian
            new_row[ExcelColumns.BRAND_CYRILLIC.value] = target_brand_ru
            new_row[ExcelColumns.MODEL_CYRILLIC.value] = target_model_ru
            # Ukrainian
            new_row[ExcelColumns.BRAND_CYRILLIC_UA.value] = target_brand_ua
            new_row[ExcelColumns.MODEL_CYRILLIC_UA.value] = target_model_ua

            if ExcelColumns.BAS_CATEGORY.value in new_row:
                new_row[ExcelColumns.BAS_CATEGORY.value] = target_model

            # Set group name and code from filtered_groups.json
            group_code = self._filtered_groups.get(target_model)
            if group_code:
                new_row[ExcelColumns.GROUP_NAME.value] = target_model
                new_row[ExcelColumns.GROUP_CODE.value] = group_code

            if self._include_record_type:
                new_row[CustomExcelColumns.RECORD_TYPE.value] = RecordTypeChoices.MIRROR.value

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
