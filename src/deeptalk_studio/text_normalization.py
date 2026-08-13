"""Reversible, deterministic normalization for Script/Transcript alignment."""

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence, Tuple


class TextNormalizationError(ValueError):
    """Normalization input or profile violates the versioned contract."""


@dataclass(frozen=True)
class NormalizedToken:
    token_id: str
    normalized_text: str
    match_keys: Tuple[str, ...]
    original_start_char: int
    original_end_char: int
    source_unit_id: str = ""
    media_start_seconds: Optional[Decimal] = None
    media_end_seconds: Optional[Decimal] = None
    timestamp_granularity: str = ""


_PROFILE = {
    "profile_version": "normalization-profile/1",
    "unicode_form": "NFKC",
    "case_mapping": "unicode_casefold",
    "punctuation_policy": "skip_preserve_span",
    "han_tokenization": "per_character_except_strict_numeric",
    "numeric_alias_policy": "strict_zh_arabic_date_percent_decimal",
}


def normalization_profile() -> dict:
    return dict(_PROFILE)


def _validate_profile(profile: Mapping[str, Any]) -> None:
    if dict(profile) != _PROFILE:
        raise TextNormalizationError("Normalization Profile 字段、顺序或版本无效")


def _is_han(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff"


_ZH_DIGITS = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_SMALL_UNITS = {"十": 10, "百": 100, "千": 1000}
_BIG_UNITS = {"万": 10_000, "亿": 100_000_000}
_ZH_NUMBER_CHARS = "零〇一二两三四五六七八九十百千万亿"


def _zh_integer(text: str, *, digit_sequence: bool = False) -> int:
    if not text or any(ch not in _ZH_NUMBER_CHARS for ch in text):
        raise TextNormalizationError("中文数字语法无效")
    if digit_sequence or not any(ch in _SMALL_UNITS or ch in _BIG_UNITS for ch in text):
        return int("".join(str(_ZH_DIGITS[ch]) for ch in text))
    total = section = number = 0
    for ch in text:
        if ch in _ZH_DIGITS:
            number = _ZH_DIGITS[ch]
        elif ch in _SMALL_UNITS:
            unit = _SMALL_UNITS[ch]
            section += (number or 1) * unit
            number = 0
        else:
            section += number
            total += section * _BIG_UNITS[ch]
            section = number = 0
    return total + section + number


def _zh_number_decimal(text: str) -> str:
    negative = text.startswith("负")
    body = text[1:] if negative else text
    if "点" in body:
        integer, fraction = body.split("点", 1)
        if not fraction or any(ch not in _ZH_DIGITS for ch in fraction):
            raise TextNormalizationError("中文小数语法无效")
        value = f"{_zh_integer(integer)}.{''.join(str(_ZH_DIGITS[ch]) for ch in fraction)}"
    else:
        value = str(_zh_integer(body))
    return f"-{value}" if negative else value


def _origin_span(mapping: Sequence[Tuple[int, int]], start: int, end: int) -> Tuple[int, int]:
    return mapping[start][0], mapping[end - 1][1]


def _mapped_nfkc(text: str) -> Tuple[str, Tuple[Tuple[int, int], ...]]:
    chars = []
    spans = []
    for index, original in enumerate(text):
        folded = unicodedata.normalize("NFKC", original).casefold()
        for char in folded:
            chars.append(char)
            spans.append((index, index + 1))
    return "".join(chars), tuple(spans)


def _structured_at(text: str, start: int) -> Optional[Tuple[int, str]]:
    tail = text[start:]
    match = re.match(r"(\d{4})[-/\u5e74](\d{1,2})[-/\u6708](\d{1,2})\u65e5?", tail)
    if match:
        return match.end(), f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    date = re.match(
        rf"([{_ZH_NUMBER_CHARS}]+)\u5e74([{_ZH_NUMBER_CHARS}]+)\u6708([{_ZH_NUMBER_CHARS}]+)\u65e5",
        tail,
    )
    if date:
        year = _zh_integer(date.group(1), digit_sequence=True)
        month = _zh_integer(date.group(2))
        day = _zh_integer(date.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return date.end(), f"{year:04d}-{month:02d}-{day:02d}"
    percent = re.match(rf"百分之(负?[{_ZH_NUMBER_CHARS}]+(?:点[{_ZH_NUMBER_CHARS}]+)?)", tail)
    if percent:
        return percent.end(), _zh_number_decimal(percent.group(1)) + "%"
    zh_number = re.match(rf"(负?[{_ZH_NUMBER_CHARS}]+(?:点[{_ZH_NUMBER_CHARS}]+)?)", tail)
    if zh_number:
        body = zh_number.group(1).lstrip("负")
        # Lone “一”/“两” are deliberately ordinary Han tokens.
        if len(body) > 1 or any(ch in _SMALL_UNITS or ch in _BIG_UNITS or ch == "点" for ch in body):
            return zh_number.end(), _zh_number_decimal(zh_number.group(1))
    arabic = re.match(r"-?\d+(?:\.\d+)?%?", tail)
    if arabic:
        raw = arabic.group(0)
        if raw.endswith("%"):
            key = str(Decimal(raw[:-1]).normalize()) + "%"
        else:
            key = str(Decimal(raw).normalize())
        return arabic.end(), key
    return None


def _tokenize(
    text: str,
    profile: Mapping[str, Any],
    *,
    unit_id: str = "",
    media_start: Optional[Decimal] = None,
    media_end: Optional[Decimal] = None,
    granularity: str = "",
    token_prefix: str = "NT",
) -> Tuple[NormalizedToken, ...]:
    _validate_profile(profile)
    if not isinstance(text, str) or not text:
        raise TextNormalizationError("待对齐文本不能为空")
    normalized, mapping = _mapped_nfkc(text)
    tokens = []
    index = 0
    while index < len(normalized):
        char = normalized[index]
        if char.isspace() or unicodedata.category(char).startswith(("P", "S")):
            index += 1
            continue
        structured = _structured_at(normalized, index)
        if structured is not None:
            length, alias = structured
            end = index + length
            value = normalized[index:end]
            start_char, end_char = _origin_span(mapping, index, end)
            keys = tuple(dict.fromkeys((value, alias)))
        elif char.isalpha() and not _is_han(char):
            end = index + 1
            while end < len(normalized) and normalized[end].isalpha() and not _is_han(normalized[end]):
                end += 1
            value = normalized[index:end]
            start_char, end_char = _origin_span(mapping, index, end)
            keys = (value,)
        else:
            end = index + 1
            value = char
            start_char, end_char = _origin_span(mapping, index, end)
            keys = (value,)
        tokens.append(
            NormalizedToken(
                token_id=f"{token_prefix}{len(tokens) + 1:06d}",
                normalized_text=value,
                match_keys=keys,
                original_start_char=start_char,
                original_end_char=end_char,
                source_unit_id=unit_id,
                media_start_seconds=media_start,
                media_end_seconds=media_end,
                timestamp_granularity=granularity,
            )
        )
        index = end
    if not tokens:
        raise TextNormalizationError("待对齐文本没有可匹配 token")
    return tuple(tokens)


def normalize_script_text(text: str, profile: Mapping[str, Any]) -> Tuple[NormalizedToken, ...]:
    return _tokenize(text, profile, token_prefix="ST")


def normalize_transcript_units(
    units: Sequence[Mapping[str, Any]],
    profile: Mapping[str, Any],
    *,
    granularity: str,
) -> Tuple[NormalizedToken, ...]:
    if granularity not in {"word", "token", "segment"}:
        raise TextNormalizationError("Transcript granularity 无效")
    output = []
    for unit in units:
        try:
            unit_id = str(unit["unit_id"])
            start = Decimal(str(unit["media_start_seconds"]))
            end = Decimal(str(unit["media_end_seconds"]))
            spoken = unit["spoken_text"]
        except (KeyError, ValueError, TypeError) as exc:
            raise TextNormalizationError("Transcript unit 字段无效") from exc
        if not unit_id or end <= start:
            raise TextNormalizationError("Transcript unit 时间范围无效")
        local = _tokenize(
            spoken,
            profile,
            unit_id=unit_id,
            media_start=start,
            media_end=end,
            granularity=granularity,
            token_prefix="TT",
        )
        for token in local:
            output.append(
                NormalizedToken(
                    **{**asdict(token), "token_id": f"TT{len(output) + 1:06d}"}
                )
            )
    if not output:
        raise TextNormalizationError("Transcript 不能为空")
    return tuple(output)


def normalization_digest(tokens: Sequence[NormalizedToken]) -> str:
    payload = []
    for token in tokens:
        item = asdict(token)
        for key in ("media_start_seconds", "media_end_seconds"):
            if item[key] is not None:
                item[key] = str(item[key])
        item["match_keys"] = list(item["match_keys"])
        payload.append(item)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
