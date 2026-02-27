from functools import lru_cache
from typing import Optional
import re
import pandas as pd

from app.core.dataclasses import TripIndex, Triplets
from app.core.enums import ExcelColumns
from app.settings import (
    BRAND_MODEL_COLUMNS,
    KEYWORDS_DROP_UNCHANGED,
    KEYWORDS_MAX_LEN,
    ALLOWED_LANGUAGES
)
from app.utils.finder import (
    pair_regex_both,
    token_to_regex,
)


@lru_cache(maxsize=4096)
def _compile_pair_patterns(
        ua_brand: str, ua_model: str,
        ru_brand: str, ru_model: str,
        en_brand: str, en_model: str,
):
    return {
        "ua": pair_regex_both(ua_brand, ua_model),
        "ru": pair_regex_both(ru_brand, ru_model),
        "en": pair_regex_both(en_brand, en_model),
    }


def _replace_pair_once(
        text: str,
        patterns: dict,
        dst_brand: str,
        dst_model: str,
        force_brand_first: bool = True
) -> str:
    if not text:
        return text
    for language in ALLOWED_LANGUAGES:
        regex_brand_model, regex_model_brand = patterns[language]
        match = regex_brand_model.search(text)
        order = "bm"
        if not match:
            match = regex_model_brand.search(text)
            order = "mb"
        if not match:
            continue
        sep = match.groupdict().get("sep") or " "
        repl = f"{dst_brand}{sep}{dst_model}" if not (
                order == "mb" and not force_brand_first) else f"{dst_model}{sep}{dst_brand}"
        return text[:match.start()] + repl + text[match.end():]
    return text


@lru_cache(maxsize=4096)
def _compile_model_regex(model_str: str) -> Optional[re.Pattern]:
    """Compile a regex to match a specific model name with word boundaries."""
    if not model_str or not model_str.strip():
        return None
    pat = r"(?<!\w)" + token_to_regex(model_str.strip()) + r"(?!\w)"
    return re.compile(pat, flags=re.IGNORECASE | re.UNICODE)


class _KeywordNormalizer:
    _CYRILLIC_RANGE = re.compile(r"[А-Яа-яЁёІіЇїЄєҐґ]")

    @staticmethod
    def _contains_cyrillic(text: str) -> bool:
        return bool(_KeywordNormalizer._CYRILLIC_RANGE.search(text))

    @staticmethod
    def _truncate_join(parts: list[str], limit: int, sep: str = ", ") -> str:
        out: list[str] = []
        total = 0
        for i, p in enumerate(parts):
            add = len(p) if not out else len(sep) + len(p)
            if total + add > limit:
                break
            out.append(p)
            total += add
        return sep.join(out)

    def normalize_cell(
            self,
            row: pd.Series,
            *,
            column: str,
            src_trip: dict,
            dst_trip: dict,
            cyrillic_lang: str,
            sep_out: str = ", ",
            deduplicate: bool = True,
            drop_unchanged: bool = KEYWORDS_DROP_UNCHANGED,
            max_len: int = KEYWORDS_MAX_LEN,
    ) -> pd.Series:
        if column not in row.index:
            return row

        raw = row.get(column)
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return row

        raw_str = str(raw).strip()
        if not raw_str:
            return row

        parts = [p.strip() for p in re.split(r"\s*,\s*", raw_str) if p.strip()]
        out, seen = [], set()

        for p in parts:
            new_p = p
            changed = False

            # Determine preferred language order based on the text:
            # - All-Latin text → try EN first (avoids lookalike Cyrillic matches)
            # - Has Cyrillic → try cyrillic_lang first
            # Use the MATCHED language for replacement so model names
            # stay in their original script.
            if self._contains_cyrillic(p):
                lang_order = [cyrillic_lang] + [l for l in ALLOWED_LANGUAGES if l != cyrillic_lang]
            else:
                lang_order = ["en"] + [l for l in ALLOWED_LANGUAGES if l != "en"]

            for lang in lang_order:
                src_model_str = src_trip[lang]["model"]
                rx = _compile_model_regex(src_model_str)
                if rx:
                    m = rx.search(p)
                    if m:
                        dst_model_str = dst_trip[lang]["model"]
                        new_p = p[:m.start()] + dst_model_str + p[m.end():]
                        changed = True
                        break

            if drop_unchanged and not changed:
                continue

            if deduplicate:
                key = new_p.casefold()
                if key in seen:
                    continue
                seen.add(key)

            out.append(new_p)

        row[column] = self._truncate_join(out, max_len, sep=sep_out)
        return row


class RowTransformer:
    def __init__(self, trip_index: TripIndex, triplets: Triplets) -> None:
        self._trip_index = trip_index
        self._triplets = triplets
        self._kw = _KeywordNormalizer()

    def _get_src_trip(self, src_brand: str, src_model: str) -> dict | None:
        return self._trip_index.get_pair(src_brand, src_model)

    def _replace_brand_model_in_col(
            self,
            row: pd.Series,
            *,
            column: str,
            src_trip: dict,
            dst_pair: Optional[dict],
            dst_lang: str,
            force_brand_first: bool = True,
    ) -> pd.Series:
        if column not in row:
            return row
        txt = row.get(column)
        txt = "" if pd.isna(txt) else str(txt)

        patterns = _compile_pair_patterns(
            src_trip["ua"]["brand"], src_trip["ua"]["model"],
            src_trip["ru"]["brand"], src_trip["ru"]["model"],
            src_trip["en"]["brand"], src_trip["en"]["model"],
        )

        if dst_pair:
            dst_brand = dst_pair[dst_lang]["brand"]
            dst_model = dst_pair[dst_lang]["model"]
        else:
            dst_brand = src_trip[dst_lang]["brand"]
            dst_model = src_trip[dst_lang]["model"]

        row[column] = _replace_pair_once(txt, patterns, dst_brand, dst_model, force_brand_first)
        return row

    def apply_all(
            self,
            row: pd.Series,
            *,
            src_brand: str,
            src_model: str,
            dst_pair: Optional[dict] = None,
    ) -> pd.Series:
        src_trip = self._get_src_trip(src_brand, src_model)
        if not src_trip:
            return row

        for col, lang in BRAND_MODEL_COLUMNS:
            row = self._replace_brand_model_in_col(
                row,
                column=col,
                src_trip=src_trip,
                dst_pair=dst_pair,
                dst_lang=lang,
                force_brand_first=True,
            )

        # Determine destination triplet for keywords
        dst_trip = dst_pair if dst_pair else src_trip

        row = self._kw.normalize_cell(
            row,
            column=ExcelColumns.KEYWORDS_RU.value,
            src_trip=src_trip,
            dst_trip=dst_trip,
            cyrillic_lang="ru",
        )

        if ExcelColumns.KEYWORDS_UA.value in row.index:
            row = self._kw.normalize_cell(
                row,
                column=ExcelColumns.KEYWORDS_UA.value,
                src_trip=src_trip,
                dst_trip=dst_trip,
                cyrillic_lang="ua",
            )

        return row
