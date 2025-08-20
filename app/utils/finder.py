import re, json, math

_SIMILAR = [
    ('A', 'А'), ('B', 'В'), ('C', 'С'), ('E', 'Е'), ('H', 'Н'),
    ('K', 'К'), ('M', 'М'), ('O', 'О'), ('P', 'Р'), ('T', 'Т'),
    ('X', 'Х'), ('Y', 'У')
]

_CYR_RANGE = r"[А-Яа-яЁёІіЇїЄєҐґ]"


def _char_class(ch: str) -> str:
    up = ch.upper()
    lo = ch.lower()
    variants = {ch, up, lo}
    for a, b in _SIMILAR:
        if up in (a, b) or lo in (a.lower(), b.lower()):
            variants |= {a, a.lower(), b, b.lower()}
    return "(?:" + "|".join(sorted({re.escape(v) for v in variants})) + ")"


def _token_to_regex(token: str) -> str:
    SEP = r"[\s\.\-_]*"
    out = []
    for ch in token:
        out.append(SEP if (ch.isspace() or ch in ".-_") else _char_class(ch))
    return "".join(out)


def _pair_regex(brand: str, model: str) -> re.Pattern:
    SEP_BM = r"(?P<sep>[\s\.\-_]*)"
    pat = r"(?<!\w)" + _token_to_regex(brand) + SEP_BM + _token_to_regex(model) + r"(?!\w)"
    return re.compile(pat, flags=re.IGNORECASE | re.UNICODE)


def load_triplets(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_trip_index(triplets) -> dict:
    idx = {}
    langs = ("ua", "ru", "en")
    for t in triplets:
        for bl in langs:
            b = t[bl]["brand"].lower()
            for ml in langs:
                m = t[ml]["model"].lower()
                idx[(b, m)] = t
    return idx


def _pair_regex_both(brand: str, model: str):
    SEP_BM = r"(?P<sep>[\s\.\-_]*)"
    pat_bm = r"(?<!\w)" + _token_to_regex(brand) + SEP_BM + _token_to_regex(model) + r"(?!\w)"
    pat_mb = r"(?<!\w)" + _token_to_regex(model) + SEP_BM + _token_to_regex(brand) + r"(?!\w)"
    rx1 = re.compile(pat_bm, flags=re.IGNORECASE | re.UNICODE)
    rx2 = re.compile(pat_mb, flags=re.IGNORECASE | re.UNICODE)
    return rx1, rx2


def replace_brand_model_anywhere(name: str, triplets: list, target_lang: str, force_brand_first: bool = False) -> str:
    if not name:
        return name
    for trip in triplets:
        for lang in ("ua", "ru", "en"):
            rx_bm, rx_mb = _pair_regex_both(trip[lang]["brand"], trip[lang]["model"])
            m1 = rx_bm.search(name)
            m2 = rx_mb.search(name)
            m = m1 or m2
            if not m:
                continue
            sep = m.groupdict().get("sep") or " "
            dst_b, dst_m = trip[target_lang]["brand"], trip[target_lang]["model"]
            if m2 and not force_brand_first:
                replacement = f"{dst_m}{sep}{dst_b}"
            else:
                replacement = f"{dst_b}{sep}{dst_m}"
            return name[:m.start()] + replacement + name[m.end():]
    return name


def replace_to_specific_pair(
        name: str,
        detect_triplets: list,
        dst_brand: str,
        dst_model: str,
        force_brand_first: bool = False
) -> str:
    if not name:
        return name
    for trip in detect_triplets:
        for lang in ("ua", "ru", "en"):
            rx_bm, rx_mb = _pair_regex_both(trip[lang]["brand"], trip[lang]["model"])
            m = rx_bm.search(name) or rx_mb.search(name)
            if not m:
                continue
            sep = m.groupdict().get("sep") or " "
            if m.re is rx_mb and not force_brand_first:
                repl = f"{dst_model}{sep}{dst_brand}"
            else:
                repl = f"{dst_brand}{sep}{dst_model}"
            return name[:m.start()] + repl + name[m.end():]
    return name


def _safe_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


def _has_cyrillic(s: str) -> bool:
    return bool(re.search(_CYR_RANGE, s))


def _split_model_tokens(s: str):
    return [t for t in re.split(r"[\s\.\-_/]+", s) if t]


def _model_regex_full(model_str: str) -> re.Pattern:
    pat = r"(?<!\w)" + _token_to_regex(model_str) + r"(?!\w)"
    return re.compile(pat, flags=re.IGNORECASE | re.UNICODE)


def _model_regex_base(model_str: str) -> re.Pattern | None:
    toks = _split_model_tokens(model_str)
    if not toks:
        return None
    base = toks[0]
    if len(base) < 2 and not any(ch.isdigit() for ch in base):
        return None
    pat = r"(?<!\w)" + _token_to_regex(base) + r"(?!\w)"
    return re.compile(pat, flags=re.IGNORECASE | re.UNICODE)


def replace_model_only(text: str, trip: dict, target_lang: str, strict_full: bool = False) -> str:
    if not text:
        return text
    dst_model = trip[target_lang]["model"]

    for lang in ("ua", "ru", "en"):
        rx_full = _model_regex_full(trip[lang]["model"])
        m = rx_full.search(text)
        if m:
            return text[:m.start()] + dst_model + text[m.end():]

    if strict_full:
        return text

    for lang in ("ua", "ru", "en"):
        rx_base = _model_regex_base(trip[lang]["model"])
        if not rx_base:
            continue
        m = rx_base.search(text)
        if m:
            return text[:m.start()] + dst_model + text[m.end():]

    return text


def replace_model_to_specific(
        text: str,
        detect_triplets: list,
        dst_model_str: str,
        strict_full: bool = False
) -> str:
    if not text:
        return text

    for trip in detect_triplets:
        for lang in ("ua", "ru", "en"):
            rx_full = _model_regex_full(trip[lang]["model"])
            m = rx_full.search(text)
            if m:
                return text[:m.start()] + dst_model_str + text[m.end():]

    if strict_full:
        return text

    for trip in detect_triplets:
        for lang in ("ua", "ru", "en"):
            rx_base = _model_regex_base(trip[lang]["model"])
            if not rx_base:
                continue
            m = rx_base.search(text)
            if m:
                return text[:m.start()] + dst_model_str + text[m.end():]

    return text


def normalize_keywords_by_script(
        row,
        column: str,
        dst_brand: str,
        dst_model: str,
        cyrillic_lang: str,
        trip_idx: dict,
        triplets: list,
        strict_full: bool = False,
        sep_out: str = ", ",
        deduplicate: bool = True,
):
    if column not in row.index:
        return row

    raw = _safe_str(row.get(column))
    if not raw:
        return row

    t_dst = trip_idx.get((str(dst_brand).lower(), str(dst_model).lower()))
    if not t_dst:
        return row

    parts = [p.strip() for p in re.split(r"\s*,\s*", raw) if p.strip()]
    out, seen = [], set()

    for p in parts:
        target_lang = cyrillic_lang if _has_cyrillic(p) else "en"
        dst_model_str = t_dst[target_lang]["model"]
        new_p = replace_model_to_specific(
            p, detect_triplets=triplets, dst_model_str=dst_model_str, strict_full=strict_full
        )

        if deduplicate:
            key = new_p.casefold()
            if key in seen:
                continue
            seen.add(key)

        out.append(new_p)

    row[column] = sep_out.join(out)
    return row
