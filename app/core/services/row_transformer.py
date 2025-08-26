from functools import lru_cache
from typing import Optional
import re
import pandas as pd

from app.core.dataclasses import TripIndex, Triplets
from app.settings import (
    BRAND_MODEL_COLUMNS,
    KEYWORDS_ALLOW_BASE_FALLBACK,
    KEYWORDS_DROP_UNCHANGED,
    KEYWORDS_MAX_LEN,
    ALLOWED_LANGUAGES
)
from app.utils.finder import (
    pair_regex_both,
    token_to_regex,
    split_model_tokens,
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


def _build_keyword_union_patterns(triplets: list[dict]):
    by_lang_full: dict[str, set[str]] = {"ua": set(), "ru": set(), "en": set()}
    by_lang_base: dict[str, set[str]] = {"ua": set(), "ru": set(), "en": set()}

    for triplet in triplets:
        for language in ALLOWED_LANGUAGES:
            model = str(triplet[language]["model"]).strip()
            if model:
                by_lang_full[language].add(token_to_regex(model))
            tokens = split_model_tokens(model)
            if tokens:
                base = tokens[0]
                if len(base) >= 2 or any(ch.isdigit() for ch in base):
                    by_lang_base[language].add(token_to_regex(base))

    def _compile_union(parts: set[str]) -> Optional[re.Pattern]:
        if not parts:
            return None
        union = "(?:" + "|".join(sorted(parts)) + ")"
        return re.compile(r"(?<!\w)" + union + r"(?!\w)", flags=re.IGNORECASE | re.UNICODE)

    full_pattern = {lang: _compile_union(parts) for lang, parts in by_lang_full.items()}
    base_pattern = {lang: _compile_union(parts) for lang, parts in by_lang_base.items()}
    return full_pattern, base_pattern


class _KeywordNormalizer:
    _CYRILLIC_RANGE = re.compile(r"[А-Яа-яЁёІіЇїЄєҐґ]")

    def __init__(self, trip_index_raw: dict, triplets_raw: list[dict]) -> None:
        self._trip_index_raw = trip_index_raw
        self._full_pattern_by_language, self._base_pattern_by_language = _build_keyword_union_patterns(triplets_raw)

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
            dst_brand: str,
            dst_model: str,
            cyrillic_lang: str,
            strict_full: bool,
            sep_out: str = ", ",
            deduplicate: bool = True,
            allow_base_fallback: bool = KEYWORDS_ALLOW_BASE_FALLBACK,
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

        t_dst = self._trip_index_raw.get((str(dst_brand).lower(), str(dst_model).lower()))
        if not t_dst:
            return row

        parts = [p.strip() for p in re.split(r"\s*,\s*", raw_str) if p.strip()]
        out, seen = [], set()

        for p in parts:
            target_lang = cyrillic_lang if self._contains_cyrillic(p) else "en"
            dst_model_str = t_dst[target_lang]["model"]

            rx_full = self._full_pattern_by_language.get(target_lang)
            rx_base = self._base_pattern_by_language.get(target_lang)

            new_p = p
            changed = False

            m = rx_full.search(p) if rx_full else None
            if m:
                new_p = p[:m.start()] + dst_model_str + p[m.end():]
                changed = True
            else:
                if (not strict_full or allow_base_fallback) and rx_base:
                    mb = rx_base.search(p)
                    if mb:
                        new_p = p[:mb.start()] + dst_model_str + p[mb.end():]
                        changed = True

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
        self._kw = _KeywordNormalizer(trip_index.raw, triplets.raw)

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

        ru_brand = (dst_pair["ru"]["brand"] if dst_pair else src_brand)
        ru_model = (dst_pair["ru"]["model"] if dst_pair else src_model)
        ua_brand = (dst_pair["ua"]["brand"] if dst_pair else src_brand)
        ua_model = (dst_pair["ua"]["model"] if dst_pair else src_model)

        row = self._kw.normalize_cell(
            row,
            column="Поисковые_запросы",
            dst_brand=ru_brand,
            dst_model=ru_model,
            cyrillic_lang="ru",
            strict_full=bool(dst_pair),
        )

        if "Ключевые_слова_ua" in row.index:
            row = self._kw.normalize_cell(
                row,
                column="Ключевые_слова_ua",
                dst_brand=ua_brand,
                dst_model=ua_model,
                cyrillic_lang="ua",
                strict_full=True,
            )
        elif "Ключевые_слова_уа" in row.index:
            row = self._kw.normalize_cell(
                row,
                column="Ключевые_слова_уа",
                dst_brand=ua_brand,
                dst_model=ua_model,
                cyrillic_lang="ua",
                strict_full=True,
            )

        return row
