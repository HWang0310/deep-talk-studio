"""Build deterministic Beat and Material Cue timelines from real timed units."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Mapping, Sequence

from .sequence_alignment import align_sequences
from .text_normalization import (
    normalization_digest,
    normalization_profile,
    normalize_script_text,
    normalize_transcript_units,
)


class AlignmentBuildError(ValueError):
    """Reviewed roots cannot form a truthful Script Alignment."""


def _data(value):
    return value.data if hasattr(value, "data") else value


def _digest(value: Mapping[str, Any], omit="artifact_digest") -> str:
    payload = deepcopy(dict(value))
    payload.pop(omit, None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _script_digest(script: Mapping[str, Any]) -> str:
    return _digest(script, omit="__absent__")


def _window_dict(window):
    return asdict(window)


def _gap_dict(gap, char_offset=0):
    value = asdict(gap)
    value["transcript_unit_ids"] = list(value["transcript_unit_ids"])
    value["script_char_start"] += char_offset
    value["script_char_end"] += char_offset
    return value


def _matched_pairs(trace):
    return {
        operation.script_token_index: operation.transcript_token_index
        for operation in trace.operations
        if operation.operation in {"primary_match", "numeric_match"}
    }


def _exact_windows(script_tokens, transcript_tokens):
    windows = []
    size = len(script_tokens)
    for start in range(0, len(transcript_tokens) - size + 1):
        if all(
            set(script_tokens[index].match_keys).intersection(transcript_tokens[start + index].match_keys)
            for index in range(size)
        ):
            windows.append((start, start + size))
    return windows


def _beat_record(beat, char_start, transcript, transcript_tokens, profile):
    script_tokens = normalize_script_text(beat["narration"], normalization_profile())
    exact_windows = _exact_windows(script_tokens, transcript_tokens)
    transcript_offset = exact_windows[0][0] if len(exact_windows) == 1 else 0
    aligned_transcript_tokens = (
        transcript_tokens[exact_windows[0][0]:exact_windows[0][1]]
        if len(exact_windows) == 1 else transcript_tokens
    )
    trace = align_sequences(script_tokens, aligned_transcript_tokens, profile)
    pairs = _matched_pairs(trace)
    matched_indices = [pairs[index] + transcript_offset for index in sorted(pairs)]
    unit_by_id = {unit["unit_id"]: unit for unit in transcript["timed_units"]}
    unit_ids = list(dict.fromkeys(
        transcript_tokens[index].source_unit_id for index in matched_indices
        if transcript_tokens[index].source_unit_id
    ))
    units = [unit_by_id[unit_id] for unit_id in unit_ids]
    token_count = len(script_tokens)
    match_count = len(pairs)
    substitutions = sum(op.operation == "substitution" for op in trace.operations)
    coverage = match_count / token_count
    similarity = max(0.0, (match_count - substitutions) / token_count)
    theoretical = token_count * float(profile["primary_match_score"])
    match_score = max(0.0, min(1.0, trace.total_score / theoretical))
    deviations = []
    operation_kinds = {operation.operation for operation in trace.operations}
    if "script_deletion" in operation_kinds:
        deviations.append("omitted_script_span")
    if "transcript_insertion" in operation_kinds:
        deviations.append("ad_lib_transcript_span")
    if trace.ambiguity_code == "ambiguous_match" or len(exact_windows) > 1:
        deviations.append("ambiguous_match")
    if any(
        gap.gap_type == "omitted_script_span"
        and gap.script_char_end - gap.script_char_start >= profile["long_gap_token_threshold"]
        for gap in trace.gaps
    ):
        deviations.append("long_gap")
    granularity = transcript["timestamp_granularity"]
    if granularity == "segment":
        deviations.append("segment_coarse")
    risk_ids = list(dict.fromkeys(
        risk_id for unit in units for risk_id in unit.get("boundary_risk_ids", [])
    ))
    if risk_ids:
        deviations.append("chunk_boundary_risk")
    accepted = profile["accepted_floors"]
    review = profile["review_floors"]
    if coverage < review["coverage"] or similarity < review["similarity"] or not units:
        status, confidence = "unmatched", "none"
    elif (
        coverage >= accepted["coverage"] and similarity >= accepted["similarity"]
        and not deviations and granularity in {"word", "token"}
    ):
        status, confidence = "aligned", "high"
    else:
        status = "needs_review"
        confidence = "medium" if trace.ambiguity_code == "none" and not risk_ids else "low"
    unique_window = len(exact_windows) <= 1 and len(trace.candidate_windows) <= 1
    has_time = bool(units) and status != "unmatched" and unique_window
    return {
        "beat_id": beat["beat_id"],
        "intended_char_start": char_start,
        "intended_char_end": char_start + len(beat["narration"]),
        "matched_transcript_unit_ids": unit_ids,
        "actual_start_seconds": units[0]["media_start_seconds"] if has_time else "",
        "actual_end_seconds": units[-1]["media_end_seconds"] if has_time else "",
        "timestamp_source": "provider_timed_transcript" if has_time else "none",
        "timestamp_granularity": granularity if has_time else "none",
        "match_score": round(match_score, 6),
        "token_coverage": round(coverage, 6),
        "similarity": round(similarity, 6),
        "confidence": confidence,
        "alignment_status": status,
        "deviation_codes": deviations,
        "deviation_summary": "、".join(deviations),
        "boundary_risk_ids": risk_ids,
        "candidate_windows": [_window_dict(window) for window in trace.candidate_windows],
        "_trace": trace,
        "_tokens": script_tokens,
        "_pairs": pairs,
        "_transcript_offset": transcript_offset,
    }


def _cue_records(cues, beats, beat_records, transcript, transcript_tokens):
    beat_by_id = {beat["beat_id"]: beat for beat in beats}
    record_by_id = {record["beat_id"]: record for record in beat_records}
    unit_by_id = {unit["unit_id"]: unit for unit in transcript["timed_units"]}
    ordered = []
    for cue in cues:
        beat = beat_by_id.get(cue.get("beat_id"))
        if beat is None:
            raise AlignmentBuildError("Material Cue 引用了未知 Beat")
        anchor = cue.get("placement_anchor", "")
        starts = []
        cursor = 0
        while anchor:
            found = beat["narration"].find(anchor, cursor)
            if found < 0:
                break
            starts.append(found)
            cursor = found + 1
        record = record_by_id[beat["beat_id"]]
        deviation = []
        matched_ids = []
        candidates = []
        actual_start = actual_end = ""
        anchor_start = anchor_end = 0
        status = "unplaced"
        confidence = "none"
        granularity = "none"
        risk_ids = []
        if len(starts) == 1:
            anchor_start = starts[0]
            anchor_end = anchor_start + len(anchor)
            token_indices = [
                index for index, token in enumerate(record["_tokens"])
                if token.original_start_char >= anchor_start and token.original_end_char <= anchor_end
            ]
            matched_transcript_indices = [
                record["_pairs"][index] + record["_transcript_offset"]
                for index in token_indices if index in record["_pairs"]
            ]
            matched_ids = list(dict.fromkeys(
                transcript_tokens[index].source_unit_id for index in matched_transcript_indices
                if transcript_tokens[index].source_unit_id
            ))
            units = [unit_by_id[unit_id] for unit_id in matched_ids]
            risk_ids = list(dict.fromkeys(risk for unit in units for risk in unit.get("boundary_risk_ids", [])))
            if units and len(matched_transcript_indices) == len(token_indices):
                actual_start, actual_end = units[0]["media_start_seconds"], units[-1]["media_end_seconds"]
                granularity = transcript["timestamp_granularity"]
                if risk_ids:
                    status, confidence = "needs_review", "low"
                elif granularity == "segment":
                    status, confidence = "coarse", "low"
                elif record["alignment_status"] == "needs_review":
                    status, confidence = "needs_review", "low"
                elif record["alignment_status"] == "aligned" and granularity in {"word", "token"}:
                    status, confidence = "aligned", "high"
            if risk_ids:
                deviation.append("chunk_boundary_risk")
        elif len(starts) > 1:
            deviation.append("ambiguous_anchor")
        else:
            deviation.append("anchor_not_found")
        ordered.append({
            "cue_id": cue["cue_id"], "beat_id": cue["beat_id"], "placement_anchor": anchor,
            "anchor_char_start": record["intended_char_start"] + anchor_start,
            "anchor_char_end": record["intended_char_start"] + anchor_end,
            "semantic_char_start": record["intended_char_start"] + anchor_start,
            "semantic_char_end": record["intended_char_end"],
            "matched_transcript_unit_ids": matched_ids,
            "actual_start_seconds": actual_start, "actual_end_seconds": actual_end,
            "placement_status": status, "timestamp_granularity": granularity,
            "confidence": confidence, "deviation_codes": deviation,
            "boundary_risk_ids": risk_ids, "candidate_windows": candidates,
        })
    # Semantic span ends at the next anchor in the same Beat.
    for index, cue in enumerate(ordered):
        later = [other for other in ordered[index + 1:] if other["beat_id"] == cue["beat_id"] and other["anchor_char_start"] > cue["anchor_char_start"]]
        if later:
            cue["semantic_char_end"] = later[0]["anchor_char_start"]
    return ordered


def build_script_alignment(script, transcript, mapping, profile, cues, *, alignment_id, created_at):
    script = _data(script)
    transcript = _data(transcript)
    mapping = _data(mapping)
    if mapping.get("mapping_id") != transcript.get("timestamp_mapping_id") or mapping.get("mapping_digest") != transcript.get("timestamp_mapping_digest"):
        raise AlignmentBuildError("Timestamp Mapping 与 Transcript 绑定不一致")
    beats = script.get("beats", [])
    if not beats or not alignment_id or not created_at:
        raise AlignmentBuildError("Script Alignment 缺少必要输入")
    transcript_tokens = normalize_transcript_units(
        transcript["timed_units"], normalization_profile(),
        granularity=transcript["timestamp_granularity"],
    )
    records = []
    char_cursor = 0
    all_operations = []
    all_windows = []
    all_gaps = []
    trace_digests = []
    for beat in beats:
        record = _beat_record(beat, char_cursor, transcript, transcript_tokens, profile)
        trace = record["_trace"]
        all_operations.extend(asdict(operation) for operation in trace.operations)
        all_windows.extend(_window_dict(window) for window in trace.candidate_windows)
        all_gaps.extend(_gap_dict(gap, char_cursor) for gap in trace.gaps)
        trace_digests.append(trace.digest)
        records.append(record)
        char_cursor += len(beat["narration"])
    cue_records = _cue_records(cues, beats, records, transcript, transcript_tokens)
    public_beats = [{key: value for key, value in record.items() if not key.startswith("_")} for record in records]
    trace_digest = _digest({"beat_trace_digests": trace_digests}, omit="__none__")
    artifact = {
        "artifact_version": "script-alignment/1", "alignment_id": alignment_id,
        "revision": 1, "created_at": created_at,
        "script_id": script.get("script_id", "SCR-unknown"), "script_revision": script.get("revision", 1),
        "script_content_digest": _script_digest(script),
        "narration_media_id": transcript["narration_media_id"],
        "narration_media_sha256": transcript["narration_media_sha256"],
        "presentation_duration_seconds": transcript["timed_units"][-1]["media_end_seconds"],
        "timestamp_mapping_id": mapping["mapping_id"], "timestamp_mapping_digest": mapping["mapping_digest"],
        "transcript_id": transcript["transcript_id"], "transcript_digest": transcript["transcript_digest"],
        "transcription_chunk_plan_digest": transcript["transcription_chunk_plan_digest"],
        "normalization_profile_version": "normalization-profile/1",
        "normalization_digest": normalization_digest(transcript_tokens),
        "alignment_profile_version": profile["artifact_version"],
        "alignment_profile_digest": profile["profile_digest"],
        "algorithm_version": profile["algorithm_version"], "alignment_trace_digest": trace_digest,
        "operations": all_operations, "candidate_windows": all_windows,
        "beat_timeline": public_beats, "cue_timeline": cue_records, "gaps": all_gaps,
    }
    artifact["artifact_digest"] = _digest(artifact)
    return artifact
