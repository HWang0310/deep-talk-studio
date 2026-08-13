"""Deterministic global alignment with explicit ambiguity and gap evidence."""

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence, Tuple

from .text_normalization import NormalizedToken


class SequenceAlignmentError(ValueError):
    """Alignment input/profile is invalid."""


@dataclass(frozen=True)
class AlignmentOperation:
    operation: str
    script_token_index: int
    transcript_token_index: int
    score: float


@dataclass(frozen=True)
class CandidateWindow:
    script_token_start: int
    script_token_end: int
    transcript_token_start: int
    transcript_token_end: int
    transcript_unit_start: str
    transcript_unit_end: str
    actual_start_seconds: str
    actual_end_seconds: str
    score: float
    normalized_margin: float


@dataclass(frozen=True)
class AlignmentGap:
    gap_id: str
    gap_type: str
    script_char_start: int
    script_char_end: int
    transcript_unit_ids: Tuple[str, ...]
    actual_start_seconds: str
    actual_end_seconds: str
    reason_code: str


@dataclass(frozen=True)
class AlignmentTrace:
    algorithm_version: str
    operations: Tuple[AlignmentOperation, ...]
    candidate_windows: Tuple[CandidateWindow, ...]
    gaps: Tuple[AlignmentGap, ...]
    ambiguity_code: str
    total_score: float
    digest: str


_REQUIRED_PROFILE = {
    "algorithm_version", "primary_match_score", "numeric_alias_match_score",
    "substitution_score", "script_deletion_score", "transcript_insertion_score",
    "ambiguity_normalized_margin",
}


def _decimal(profile: Mapping[str, Any], key: str) -> Decimal:
    try:
        return Decimal(str(profile[key]))
    except (KeyError, ValueError, TypeError) as exc:
        raise SequenceAlignmentError(f"Alignment Profile 缺少有效字段：{key}") from exc


def _match_kind(left: NormalizedToken, right: NormalizedToken) -> str:
    if left.normalized_text == right.normalized_text:
        return "primary_match"
    if set(left.match_keys).intersection(right.match_keys):
        return "numeric_match"
    return "substitution"


def _operation_score(kind: str, profile: Mapping[str, Any]) -> Decimal:
    key = {
        "primary_match": "primary_match_score",
        "numeric_match": "numeric_alias_match_score",
        "substitution": "substitution_score",
        "script_deletion": "script_deletion_score",
        "transcript_insertion": "transcript_insertion_score",
    }[kind]
    return _decimal(profile, key)


def _best_candidate(candidates):
    # Stable path priority: primary, numeric, insertion, deletion, substitution,
    # then earlier transcript index already follows deterministic matrix order.
    rank = {"primary_match": 0, "numeric_match": 1, "transcript_insertion": 2,
            "script_deletion": 3, "substitution": 4}
    return max(candidates, key=lambda item: (item[0], -rank[item[1]], -item[3]))


def _full_dp(script, transcript, profile):
    n, m = len(script), len(transcript)
    deletion = _operation_score("script_deletion", profile)
    insertion = _operation_score("transcript_insertion", profile)
    scores = [[Decimal(0) for _ in range(m + 1)] for _ in range(n + 1)]
    back = [[None for _ in range(m + 1)] for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0] = scores[i - 1][0] + deletion
        back[i][0] = (i - 1, 0, "script_deletion", deletion)
    for j in range(1, m + 1):
        scores[0][j] = scores[0][j - 1] + insertion
        back[0][j] = (0, j - 1, "transcript_insertion", insertion)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            kind = _match_kind(script[i - 1], transcript[j - 1])
            diagonal = _operation_score(kind, profile)
            choice = _best_candidate((
                (scores[i - 1][j - 1] + diagonal, kind, (i - 1, j - 1), j - 1, diagonal),
                (scores[i][j - 1] + insertion, "transcript_insertion", (i, j - 1), j - 1, insertion),
                (scores[i - 1][j] + deletion, "script_deletion", (i - 1, j), j, deletion),
            ))
            scores[i][j] = choice[0]
            back[i][j] = (*choice[2], choice[1], choice[4])
    operations = []
    i, j = n, m
    while i or j:
        previous_i, previous_j, kind, delta = back[i][j]
        if kind == "transcript_insertion":
            script_index, transcript_index = -1, j - 1
        elif kind == "script_deletion":
            script_index, transcript_index = i - 1, -1
        else:
            script_index, transcript_index = i - 1, j - 1
        operations.append(AlignmentOperation(kind, script_index, transcript_index, float(delta)))
        i, j = previous_i, previous_j
    operations.reverse()
    return tuple(operations), scores[n][m]


def _window_candidates(script, transcript, profile):
    n, m = len(script), len(transcript)
    if n > m:
        return ()
    scored = []
    for start in range(m - n + 1):
        score = sum(
            (_operation_score(_match_kind(script[index], transcript[start + index]), profile)
             for index in range(n)),
            Decimal(0),
        )
        scored.append((start, score))
    best = max(score for _, score in scored)
    theoretical = max(Decimal(1), Decimal(n) * _decimal(profile, "primary_match_score"))
    margin_limit = _decimal(profile, "ambiguity_normalized_margin")
    windows = []
    for start, score in scored:
        margin = (best - score) / theoretical
        if margin > margin_limit:
            continue
        first, last = transcript[start], transcript[start + n - 1]
        windows.append(
            CandidateWindow(
                script_token_start=0, script_token_end=n,
                transcript_token_start=start, transcript_token_end=start + n,
                transcript_unit_start=first.source_unit_id,
                transcript_unit_end=last.source_unit_id,
                actual_start_seconds=str(first.media_start_seconds or ""),
                actual_end_seconds=str(last.media_end_seconds or ""),
                score=float(score), normalized_margin=float(margin),
            )
        )
    return tuple(windows)


def _group_gaps(operations, script, transcript):
    output = []
    index = 0
    while index < len(operations):
        operation = operations[index]
        if operation.operation not in {"script_deletion", "transcript_insertion"}:
            index += 1
            continue
        kind = operation.operation
        group = []
        while index < len(operations) and operations[index].operation == kind:
            group.append(operations[index])
            index += 1
        if kind == "script_deletion":
            selected = [script[item.script_token_index] for item in group]
            char_start, char_end = selected[0].original_start_char, selected[-1].original_end_char
            units, start, end = (), "", ""
            gap_type, reason = "omitted_script_span", "script_tokens_without_transcript"
        else:
            selected = [transcript[item.transcript_token_index] for item in group]
            char_start = char_end = 0
            units = tuple(dict.fromkeys(token.source_unit_id for token in selected if token.source_unit_id))
            start, end = str(selected[0].media_start_seconds or ""), str(selected[-1].media_end_seconds or "")
            gap_type, reason = "ad_lib_transcript_span", "transcript_tokens_without_script"
        output.append(AlignmentGap(
            gap_id=f"GAP{len(output) + 1:04d}", gap_type=gap_type,
            script_char_start=char_start, script_char_end=char_end,
            transcript_unit_ids=units, actual_start_seconds=start,
            actual_end_seconds=end, reason_code=reason,
        ))
    return tuple(output)


def _trace_digest(operations, windows, gaps, ambiguity, total):
    payload = {
        "algorithm_version": "alignment-algorithm/1",
        "operations": [asdict(value) for value in operations],
        "candidate_windows": [asdict(value) for value in windows],
        "gaps": [{**asdict(value), "transcript_unit_ids": list(value.transcript_unit_ids)} for value in gaps],
        "ambiguity_code": ambiguity, "total_score": float(total),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _align(script_tokens, transcript_tokens, profile):
    if not script_tokens or not transcript_tokens:
        raise SequenceAlignmentError("Script/Transcript token stream 不能为空")
    if not _REQUIRED_PROFILE.issubset(profile) or profile["algorithm_version"] != "alignment-algorithm/1":
        raise SequenceAlignmentError("Alignment Profile 与 algorithm/1 不匹配")
    operations, total = _full_dp(script_tokens, transcript_tokens, profile)
    windows = _window_candidates(script_tokens, transcript_tokens, profile)
    ambiguity = "ambiguous_match" if len(windows) > 1 else "none"
    gaps = _group_gaps(operations, script_tokens, transcript_tokens)
    if ambiguity == "ambiguous_match":
        first, last = script_tokens[0], script_tokens[-1]
        gaps = gaps + (AlignmentGap(
            gap_id=f"GAP{len(gaps) + 1:04d}", gap_type="repeated_or_ambiguous_span",
            script_char_start=first.original_start_char, script_char_end=last.original_end_char,
            transcript_unit_ids=tuple(dict.fromkeys(
                unit for window in windows for unit in (window.transcript_unit_start, window.transcript_unit_end) if unit
            )), actual_start_seconds=windows[0].actual_start_seconds,
            actual_end_seconds=windows[-1].actual_end_seconds, reason_code="candidate_margin_tie",
        ),)
    digest = _trace_digest(operations, windows, gaps, ambiguity, total)
    return AlignmentTrace("alignment-algorithm/1", operations, windows, gaps, ambiguity, float(total), digest)


def align_sequences(script_tokens, transcript_tokens, profile) -> AlignmentTrace:
    # algorithm/1 reserves checkpoint recomputation as a memory optimization. The
    # canonical result is deliberately delegated to the full reference today.
    return _align(tuple(script_tokens), tuple(transcript_tokens), profile)


def _align_sequences_full_reference(script_tokens, transcript_tokens, profile) -> AlignmentTrace:
    return _align(tuple(script_tokens), tuple(transcript_tokens), profile)


def rederive_alignment_trace(script_tokens, transcript_tokens, profile) -> AlignmentTrace:
    return align_sequences(script_tokens, transcript_tokens, profile)
