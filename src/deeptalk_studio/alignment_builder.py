"""Build deterministic global Script→Transcript projections for Beats and Cues."""

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal, InvalidOperation

from .sequence_alignment import align_sequences
from .text_normalization import normalization_digest, normalization_profile, normalize_script_text, normalize_transcript_units


class AlignmentBuildError(ValueError):
    """Reviewed roots cannot form a truthful Script Alignment."""


_DIRECT = {"primary_match", "numeric_match"}
_MAPPED = _DIRECT | {"substitution"}


def _data(value):
    return value.data if hasattr(value, "data") else value


def _digest(value, omit="artifact_digest"):
    payload = deepcopy(dict(value)); payload.pop(omit, None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _script_digest(script):
    return _digest(script, omit="__absent__")


def _global_script_tokens(beats):
    tokens, spans, char_cursor = [], [], 0
    for beat in beats:
        local = normalize_script_text(beat["narration"], normalization_profile())
        token_start = len(tokens)
        for token in local:
            tokens.append(replace(
                token, token_id=f"GS{len(tokens) + 1:06d}",
                original_start_char=token.original_start_char + char_cursor,
                original_end_char=token.original_end_char + char_cursor,
            ))
        spans.append({"beat_id": beat["beat_id"], "char_start": char_cursor,
                      "char_end": char_cursor + len(beat["narration"]),
                      "script_token_start": token_start, "script_token_end": len(tokens)})
        char_cursor += len(beat["narration"])
    return tuple(tokens), tuple(spans)


def _span_for_index(index, spans):
    return next((span for span in spans if span["script_token_start"] <= index < span["script_token_end"]), None)


def _time(token_index, tokens):
    token = tokens[token_index]
    return {"transcript_token_index": token_index, "transcript_unit_id": token.source_unit_id,
            "actual_start_seconds": str(token.media_start_seconds) if token.media_start_seconds is not None else "",
            "actual_end_seconds": str(token.media_end_seconds) if token.media_end_seconds is not None else ""}


def _global_mapping(script_tokens, transcript_tokens, profile, spans):
    """The one and only whole Script / whole Transcript evidence pass."""
    trace = align_sequences(script_tokens, transcript_tokens, profile, inspect_candidate_windows=False)
    script_units = [None] * len(script_tokens)
    inserts = []
    for operation_index, operation in enumerate(trace.operations):
        if operation.operation == "transcript_insertion":
            inserts.append((operation_index, operation)); continue
        token = script_tokens[operation.script_token_index]
        value = {"script_token_index": operation.script_token_index,
                 "script_char_start": token.original_start_char, "script_char_end": token.original_end_char,
                 "operation": operation.operation}
        value.update(_time(operation.transcript_token_index, transcript_tokens) if operation.transcript_token_index >= 0 else
                     {"transcript_token_index": -1, "transcript_unit_id": "", "actual_start_seconds": "", "actual_end_seconds": ""})
        script_units[operation.script_token_index] = value
    if any(item is None for item in script_units):
        raise AlignmentBuildError("全局 Script 对齐缺少 lexical unit correspondence")
    insertion_records = []
    for operation_index, operation in inserts:
        left = next((item.script_token_index for item in reversed(trace.operations[:operation_index]) if item.script_token_index >= 0), -1)
        right = next((item.script_token_index for item in trace.operations[operation_index + 1:] if item.script_token_index >= 0), -1)
        left_span = _span_for_index(left, spans) if left >= 0 else None
        right_span = _span_for_index(right, spans) if right >= 0 else None
        if right < 0:
            ownership, owner = "trailing", ""
        elif left < 0:
            ownership, owner = "leading", ""
        elif left_span and right_span and left_span["beat_id"] == right_span["beat_id"]:
            ownership, owner = "beat_local", left_span["beat_id"]
        else:
            ownership, owner = "beat_boundary", ""
        item = _time(operation.transcript_token_index, transcript_tokens)
        item.update({"left_script_token_index": left, "right_script_token_index": right,
                     "ownership": ownership, "owner_beat_id": owner})
        insertion_records.append(item)
    return trace, {"mapping_version": "global-monotonic-projection/1", "trace_digest": trace.digest,
                   "script_token_count": len(script_tokens), "transcript_token_count": len(transcript_tokens),
                   "ambiguity_code": trace.ambiguity_code, "script_units": script_units,
                   "transcript_insertions": insertion_records}


def _units(indices, transcript_tokens, units_by_id):
    ids = list(dict.fromkeys(transcript_tokens[index].source_unit_id for index in sorted(indices)
                             if transcript_tokens[index].source_unit_id))
    return ids, [units_by_id[unit_id] for unit_id in ids]


def _long_deletion(records, threshold):
    run = 0
    for record in records:
        run = run + 1 if record["operation"] == "script_deletion" else 0
        if run >= threshold:
            return True
    return False


def _beat_records(spans, mapping, trace, transcript, transcript_tokens, profile):
    units_by_id = {unit["unit_id"]: unit for unit in transcript["timed_units"]}
    score_by_script = {item.script_token_index: item.score for item in trace.operations if item.script_token_index >= 0}
    records = []
    for span in spans:
        local = mapping["script_units"][span["script_token_start"]:span["script_token_end"]]
        inserts = [item for item in mapping["transcript_insertions"]
                   if item["ownership"] == "beat_local" and item["owner_beat_id"] == span["beat_id"]]
        indexes = [item["transcript_token_index"] for item in local if item["operation"] in _MAPPED]
        indexes.extend(item["transcript_token_index"] for item in inserts)
        unit_ids, units = _units(indexes, transcript_tokens, units_by_id)
        count = len(local); direct = sum(item["operation"] in _DIRECT for item in local)
        substitutions = sum(item["operation"] == "substitution" for item in local)
        coverage, similarity = direct / count, (direct + substitutions) / count
        score = sum(score_by_script[index] for index in range(span["script_token_start"], span["script_token_end"]))
        match_score = max(0.0, min(1.0, score / (count * float(profile["primary_match_score"]))))
        deviations = []
        if any(item["operation"] == "script_deletion" for item in local): deviations.append("omitted_script_span")
        if inserts: deviations.append("ad_lib_transcript_span")
        long_gap = _long_deletion(local, profile["long_gap_token_threshold"])
        if long_gap: deviations.append("long_gap")
        if trace.ambiguity_code == "ambiguous_match": deviations.append("ambiguous_match")
        granularity = transcript["timestamp_granularity"]
        if granularity == "segment": deviations.append("segment_coarse")
        risks = list(dict.fromkeys(risk for unit in units for risk in unit.get("boundary_risk_ids", [])))
        if risks: deviations.append("chunk_boundary_risk")
        accepted = profile["accepted_floors"]; review = profile["review_floors"]
        pass_accepted = (coverage >= accepted["coverage"] and similarity >= accepted["similarity"]
                         and not long_gap and trace.ambiguity_code == "none" and not risks
                         and granularity in {"word", "token"})
        if coverage < review["coverage"] or similarity < review["similarity"] or not units:
            status, confidence = "unmatched", "none"
        elif pass_accepted:
            status, confidence = "aligned", "high"
        else:
            status, confidence = "needs_review", "medium" if trace.ambiguity_code == "none" and not risks else "low"
        has_time = bool(units) and status != "unmatched"
        records.append({"beat_id": span["beat_id"], "intended_char_start": span["char_start"], "intended_char_end": span["char_end"],
                        "matched_transcript_unit_ids": unit_ids,
                        "actual_start_seconds": units[0]["media_start_seconds"] if has_time else "",
                        "actual_end_seconds": units[-1]["media_end_seconds"] if has_time else "",
                        "timestamp_source": "provider_timed_transcript" if has_time else "none",
                        "timestamp_granularity": granularity if has_time else "none",
                        "match_score": round(match_score, 6), "token_coverage": round(coverage, 6), "similarity": round(similarity, 6),
                        "confidence": confidence, "alignment_status": status, "deviation_codes": deviations,
                        "deviation_summary": "、".join(deviations), "boundary_risk_ids": risks, "candidate_windows": [],
                        "_script_units": local})
    return records


def _gaps(trace, script_tokens, transcript_tokens, mapping):
    insertion_map = {item["transcript_token_index"]: item for item in mapping["transcript_insertions"]}
    output, index = [], 0
    while index < len(trace.operations):
        operation = trace.operations[index]
        if operation.operation not in {"script_deletion", "transcript_insertion"}:
            index += 1; continue
        kind, group = operation.operation, []
        while index < len(trace.operations) and trace.operations[index].operation == kind:
            group.append(trace.operations[index]); index += 1
        if kind == "script_deletion":
            selected = [script_tokens[item.script_token_index] for item in group]
            gap = {"gap_type": "omitted_script_span", "script_char_start": selected[0].original_start_char,
                   "script_char_end": selected[-1].original_end_char, "transcript_unit_ids": [],
                   "actual_start_seconds": "", "actual_end_seconds": "", "reason_code": "script_tokens_without_transcript"}
        else:
            selected = [transcript_tokens[item.transcript_token_index] for item in group]
            trailing = all(insertion_map[item.transcript_token_index]["ownership"] == "trailing" for item in group)
            gap = {"gap_type": "trailing_ad_lib_transcript_span" if trailing else "ad_lib_transcript_span",
                   "script_char_start": 0, "script_char_end": 0,
                   "transcript_unit_ids": list(dict.fromkeys(item.source_unit_id for item in selected if item.source_unit_id)),
                   "actual_start_seconds": str(selected[0].media_start_seconds), "actual_end_seconds": str(selected[-1].media_end_seconds),
                   "reason_code": "post_script_transcript_tail" if trailing else "transcript_tokens_without_script"}
        output.append({"gap_id": f"GAP{len(output)+1:04d}", **gap})
    if trace.ambiguity_code == "ambiguous_match":
        gap = trace.gaps[-1]
        output.append({"gap_id": f"GAP{len(output)+1:04d}", "gap_type": "repeated_or_ambiguous_span",
                       "script_char_start": gap.script_char_start, "script_char_end": gap.script_char_end,
                       "transcript_unit_ids": list(gap.transcript_unit_ids), "actual_start_seconds": gap.actual_start_seconds,
                       "actual_end_seconds": gap.actual_end_seconds, "reason_code": gap.reason_code})
    return output


def _cue_records(cues, beats, records, transcript, transcript_tokens, profile):
    beat_by_id = {beat["beat_id"]: beat for beat in beats}; record_by_id = {record["beat_id"]: record for record in records}
    units_by_id = {unit["unit_id"]: unit for unit in transcript["timed_units"]}; output = []
    for cue in cues:
        beat = beat_by_id.get(cue.get("beat_id"))
        if beat is None: raise AlignmentBuildError("Material Cue 引用了未知 Beat")
        anchor = cue.get("placement_anchor", ""); starts = []; cursor = 0
        while anchor:
            found = beat["narration"].find(anchor, cursor)
            if found < 0: break
            starts.append(found); cursor = found + 1
        record = record_by_id[beat["beat_id"]]; deviations = []
        if len(starts) == 1:
            start, end = starts[0], starts[0] + len(anchor)
        elif len(starts) > 1:
            start = end = 0; deviations.append("ambiguous_anchor")
        else:
            start = end = 0; deviations.append("anchor_not_found")
        output.append({"cue_id": cue["cue_id"], "beat_id": cue["beat_id"], "placement_anchor": anchor,
                       "anchor_char_start": record["intended_char_start"] + start, "anchor_char_end": record["intended_char_start"] + end,
                       "semantic_char_start": record["intended_char_start"] + start, "semantic_char_end": record["intended_char_end"],
                       "matched_transcript_unit_ids": [], "actual_start_seconds": "", "actual_end_seconds": "",
                       "placement_status": "unplaced", "timestamp_granularity": "none", "confidence": "none",
                       "deviation_codes": deviations, "boundary_risk_ids": [], "candidate_windows": []})
    for index, cue in enumerate(output):
        later = [other for other in output[index+1:] if other["beat_id"] == cue["beat_id"] and other["anchor_char_start"] > cue["anchor_char_start"]]
        if later: cue["semantic_char_end"] = later[0]["anchor_char_start"]
    for cue in output:
        if cue["deviation_codes"]: continue
        local = record_by_id[cue["beat_id"]]["_script_units"]
        semantic = [item for item in local if item["script_char_start"] >= cue["semantic_char_start"] and item["script_char_end"] <= cue["semantic_char_end"]]
        anchor = [item for item in semantic if item["script_char_start"] >= cue["anchor_char_start"] and item["script_char_end"] <= cue["anchor_char_end"]]
        if not anchor:
            cue["deviation_codes"].append("anchor_not_tokenized"); continue
        if any(item["operation"] not in _MAPPED for item in semantic):
            cue["deviation_codes"].append("semantic_span_unmatched"); continue
        mapped = [item["transcript_token_index"] for item in semantic]
        if mapped != sorted(mapped) or len(set(mapped)) != len(mapped):
            cue["deviation_codes"].append("semantic_span_ambiguous"); continue
        ids, units = _units(mapped, transcript_tokens, units_by_id)
        anchor_id = transcript_tokens[anchor[0]["transcript_token_index"]].source_unit_id
        if not ids or not anchor_id:
            cue["deviation_codes"].append("semantic_span_unmatched"); continue
        cue.update({"matched_transcript_unit_ids": ids,
                    "actual_start_seconds": units_by_id[anchor_id]["media_start_seconds"],
                    "actual_end_seconds": units[-1]["media_end_seconds"],
                    "timestamp_granularity": transcript["timestamp_granularity"]})
        risks = list(dict.fromkeys(risk for unit in units for risk in unit.get("boundary_risk_ids", [])))
        cue["boundary_risk_ids"] = risks
        direct = sum(item["operation"] in _DIRECT for item in semantic); substitution = sum(item["operation"] == "substitution" for item in semantic)
        coverage, similarity = direct / len(semantic), (direct + substitution) / len(semantic)
        if risks:
            cue["deviation_codes"].append("chunk_boundary_risk"); cue["placement_status"], cue["confidence"] = "needs_review", "low"
        elif transcript["timestamp_granularity"] == "segment": cue["placement_status"], cue["confidence"] = "coarse", "low"
        elif coverage >= profile["accepted_floors"]["coverage"] and similarity >= profile["accepted_floors"]["similarity"]:
            cue["placement_status"], cue["confidence"] = "aligned", "high"
        elif coverage >= profile["review_floors"]["coverage"] and similarity >= profile["review_floors"]["similarity"]:
            cue["placement_status"], cue["confidence"] = "needs_review", "medium"
        else:
            cue["deviation_codes"].append("semantic_span_low_confidence")
    return output


def build_script_alignment(script, transcript, mapping, profile, cues, *, alignment_id, created_at, media):
    script, transcript, mapping, media = _data(script), _data(transcript), _data(mapping), _data(media)
    if mapping.get("mapping_id") != transcript.get("timestamp_mapping_id") or mapping.get("mapping_digest") != transcript.get("timestamp_mapping_digest"):
        raise AlignmentBuildError("Timestamp Mapping 与 Transcript 绑定不一致")
    if media.get("media_id") != transcript.get("narration_media_id") or media.get("sha256") != transcript.get("narration_media_sha256"):
        raise AlignmentBuildError("Clean A-roll Media 与 Transcript 绑定不一致")
    try:
        duration = Decimal(str(media["presentation_duration_seconds"])); last_end = Decimal(str(transcript["timed_units"][-1]["media_end_seconds"]))
    except (KeyError, IndexError, InvalidOperation) as exc:
        raise AlignmentBuildError("Clean A-roll Media 缺少可信的成片时长") from exc
    if duration <= 0 or duration < last_end: raise AlignmentBuildError("Clean A-roll Media 时长不能短于最后一个真实转写单位")
    beats = script.get("beats", [])
    if not beats or not alignment_id or not created_at: raise AlignmentBuildError("Script Alignment 缺少必要输入")
    transcript_tokens = normalize_transcript_units(transcript["timed_units"], normalization_profile(), granularity=transcript["timestamp_granularity"])
    script_tokens, spans = _global_script_tokens(beats)
    trace, global_mapping = _global_mapping(script_tokens, transcript_tokens, profile, spans)
    records = _beat_records(spans, global_mapping, trace, transcript, transcript_tokens, profile)
    artifact = {"artifact_version": "script-alignment/2", "alignment_id": alignment_id, "revision": 1, "created_at": created_at,
                "script_id": script.get("script_id", "SCR-unknown"), "script_revision": script.get("revision", 1), "script_content_digest": _script_digest(script),
                "narration_media_id": transcript["narration_media_id"], "narration_media_sha256": transcript["narration_media_sha256"],
                "presentation_duration_seconds": str(media["presentation_duration_seconds"]),
                "timestamp_mapping_id": mapping["mapping_id"], "timestamp_mapping_digest": mapping["mapping_digest"],
                "transcript_id": transcript["transcript_id"], "transcript_digest": transcript["transcript_digest"],
                "transcription_chunk_plan_digest": transcript["transcription_chunk_plan_digest"], "normalization_profile_version": "normalization-profile/1",
                "normalization_digest": normalization_digest(transcript_tokens), "alignment_profile_version": profile["artifact_version"],
                "alignment_profile_digest": profile["profile_digest"], "algorithm_version": profile["algorithm_version"],
                "alignment_trace_digest": trace.digest, "global_mapping": global_mapping,
                "operations": [asdict(item) for item in trace.operations], "candidate_windows": [asdict(item) for item in trace.candidate_windows],
                "beat_timeline": [{key: value for key, value in record.items() if not key.startswith("_")} for record in records],
                "cue_timeline": _cue_records(cues, beats, records, transcript, transcript_tokens, profile),
                "gaps": _gaps(trace, script_tokens, transcript_tokens, global_mapping)}
    artifact["artifact_digest"] = _digest(artifact)
    return artifact
