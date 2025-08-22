from typing import Iterable


def dedupe_models(raw_compat: str | None) -> list[str]:
    if raw_compat is None:
        return []
    parts = {part.strip() for part in str(raw_compat).split(",") if str(part).strip()}
    return sorted(parts)


def same_pair(a_brand: str, a_model: str, b_brand: str, b_model: str) -> bool:
    return str(a_brand).strip().lower() == str(b_brand).strip().lower() and \
        str(a_model).strip().lower() == str(b_model).strip().lower()


def clear_fields(row, fields: Iterable[str]):
    for field in fields:
        if field in row:
            row[field] = None
    return row
