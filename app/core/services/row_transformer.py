from typing import Optional
import pandas as pd

from app.core.dataclasses import TripIndex, Triplets
from app.utils.finder import (
    replace_brand_model_anywhere,
    replace_to_specific_pair,
    normalize_keywords_by_script,
)
from app.config import BRAND_MODEL_COLUMNS


class RowTransformer:
    """Performs all text replacements within a single DataFrame row."""

    def __init__(self, trip_index: TripIndex, triplets: Triplets) -> None:
        self._trip_index = trip_index
        self._triplets = triplets

    def _replace_brand_model_in_col(
            self,
            row: pd.Series,
            *,
            column: str,
            src_brand: str,
            src_model: str,
            dst_pair: Optional[dict],
            dst_lang: str,
            force_brand_first: bool = True,
    ) -> pd.Series:
        if column not in row:
            return row
        txt = row.get(column)
        txt = "" if pd.isna(txt) else str(txt)

        if dst_pair:
            new_txt = replace_to_specific_pair(
                txt,
                self._triplets.raw,
                dst_pair[dst_lang]["brand"],
                dst_pair[dst_lang]["model"],
                force_brand_first=force_brand_first,
            )
        else:
            t = self._trip_index.get_pair(src_brand, src_model)
            if not t:
                return row
            new_txt = replace_brand_model_anywhere(
                txt, [t], dst_lang, force_brand_first=force_brand_first
            )

        row[column] = new_txt
        return row

    def apply_all(
            self,
            row: pd.Series,
            *,
            src_brand: str,
            src_model: str,
            dst_pair: Optional[dict] = None,
    ) -> pd.Series:
        # Replaces brand and model in all relevant columns of the row
        for col, lang in BRAND_MODEL_COLUMNS:
            row = self._replace_brand_model_in_col(
                row,
                column=col,
                src_brand=src_brand,
                src_model=src_model,
                dst_pair=dst_pair,
                dst_lang=lang,
                force_brand_first=True,
            )

        # Normalization of keywords data
        ru_brand = (dst_pair["ru"]["brand"] if dst_pair else src_brand)
        ru_model = (dst_pair["ru"]["model"] if dst_pair else src_model)
        ua_brand = (dst_pair["ua"]["brand"] if dst_pair else src_brand)
        ua_model = (dst_pair["ua"]["model"] if dst_pair else src_model)

        row = normalize_keywords_by_script(
            row,
            column="Поисковые_запросы",
            dst_brand=ru_brand,
            dst_model=ru_model,
            cyrillic_lang="ru",
            trip_idx=self._trip_index.raw,
            triplets=self._triplets.raw,
            strict_full=bool(dst_pair),
        )

        ua_col = "Ключевые_слова_ua" if "Ключевые_слова_ua" in row else \
            ("Ключевые_слова_уа" if "Ключевые_слова_уа" in row else None)
        if ua_col:
            row = normalize_keywords_by_script(
                row,
                column=ua_col,
                dst_brand=ua_brand,
                dst_model=ua_model,
                cyrillic_lang="ua",
                trip_idx=self._trip_index.raw,
                triplets=self._triplets.raw,
                strict_full=True,
            )
        return row
