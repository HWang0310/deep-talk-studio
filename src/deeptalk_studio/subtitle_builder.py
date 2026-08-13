"""Deterministic Timed Transcript to Basic Subtitle V1 artifact."""
import hashlib
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation


class SubtitleArtifactError(ValueError):
    pass


def _digest(value):
    payload = dict(value); payload.pop("artifact_digest", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def normalize_subtitle_text(value):
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"\s+([，。！？；：、])", r"\1", text)
    text = text.replace(",", "，").replace("!", "！").replace("?", "？")
    if not text:
        raise SubtitleArtifactError("字幕文本不能为空")
    return text


def _validate_roots(transcript, media):
    if transcript.get("artifact_version") != "timed-transcript/1" or transcript.get("timestamp_granularity") not in {"word", "token", "segment"}:
        raise SubtitleArtifactError("Timed Transcript 版本或精度无效")
    if transcript.get("narration_media_id") != media.get("media_id") or transcript.get("narration_media_sha256") != media.get("sha256"):
        raise SubtitleArtifactError("Subtitle Media binding 不一致")


def _should_join(current, unit, profile):
    if not current:
        return True
    if len("".join(item["spoken_text"] for item in current) + unit["spoken_text"]) > int(profile["max_lines"]) * int(profile["max_chars_per_line"]):
        return False
    if Decimal(unit["media_start_seconds"]) - Decimal(current[-1]["media_end_seconds"]) > Decimal(profile["max_join_gap_seconds"]):
        return False
    if Decimal(unit["media_end_seconds"]) - Decimal(current[0]["media_start_seconds"]) > Decimal(profile["max_cue_duration_seconds"]):
        return False
    return not re.search(r"[。！？!?]\s*$", current[-1]["spoken_text"])


def _cue(units, order, precision):
    text = normalize_subtitle_text("".join(str(item["spoken_text"]) for item in units))
    return {
        "cue_id": f"SUBC{order:06d}", "order": order,
        "in_seconds": str(units[0]["media_start_seconds"]),
        "out_seconds": str(units[-1]["media_end_seconds"]),
        "text": text,
        "timing_precision": "segment" if precision == "segment" else "word",
        "source_unit_ids": [str(item["unit_id"]) for item in units],
    }


def build_subtitle_artifact(transcript, media, profile, *, subtitle_id, created_at):
    _validate_roots(transcript, media)
    units = list(transcript.get("timed_units", []))
    groups = []
    if transcript["timestamp_granularity"] == "segment":
        groups = [[unit] for unit in units]
    else:
        current = []
        for unit in units:
            normalize_subtitle_text(unit.get("spoken_text", ""))
            if current and not _should_join(current, unit, profile):
                groups.append(current); current = []
            current.append(unit)
        if current:
            groups.append(current)
    artifact = {
        "artifact_version": "subtitle-artifact/1", "subtitle_id": subtitle_id,
        "revision": 1, "created_at": created_at,
        "narration_media_id": media["media_id"], "narration_media_sha256": media["sha256"],
        "transcript_id": transcript["transcript_id"], "transcript_revision": transcript["revision"],
        "transcript_digest": transcript["transcript_digest"],
        "source_timestamp_granularity": transcript["timestamp_granularity"],
        "profile_version": profile["artifact_version"], "profile_digest": profile["profile_digest"],
        "cues": [_cue(group, index, transcript["timestamp_granularity"]) for index, group in enumerate(groups)],
    }
    artifact["artifact_digest"] = _digest(artifact)
    validate_subtitle_artifact(artifact, transcript, media, profile)
    return artifact


def validate_subtitle_artifact(artifact, transcript, media, profile):
    _validate_roots(transcript, media)
    required = {"artifact_version", "subtitle_id", "revision", "created_at", "narration_media_id", "narration_media_sha256", "transcript_id", "transcript_revision", "transcript_digest", "source_timestamp_granularity", "profile_version", "profile_digest", "cues", "artifact_digest"}
    if set(artifact) != required or artifact.get("artifact_version") != "subtitle-artifact/1" or artifact.get("revision") != 1:
        raise SubtitleArtifactError("Subtitle Artifact schema 无效")
    expected_roots = (media["media_id"], media["sha256"], transcript["transcript_id"], transcript["revision"], transcript["transcript_digest"], transcript["timestamp_granularity"], profile["artifact_version"], profile["profile_digest"])
    actual_roots = (artifact["narration_media_id"], artifact["narration_media_sha256"], artifact["transcript_id"], artifact["transcript_revision"], artifact["transcript_digest"], artifact["source_timestamp_granularity"], artifact["profile_version"], artifact["profile_digest"])
    if actual_roots != expected_roots:
        raise SubtitleArtifactError("Subtitle root binding 不一致")
    source = {unit["unit_id"]: unit for unit in transcript["timed_units"]}
    previous = Decimal("-1")
    duration = Decimal(str(media["presentation_duration_seconds"]))
    for order, cue in enumerate(artifact["cues"]):
        if set(cue) != {"cue_id", "order", "in_seconds", "out_seconds", "text", "timing_precision", "source_unit_ids"} or cue["cue_id"] != f"SUBC{order:06d}" or cue["order"] != order:
            raise SubtitleArtifactError("Subtitle cue identity 无效")
        if not cue["source_unit_ids"] or any(uid not in source for uid in cue["source_unit_ids"]):
            raise SubtitleArtifactError("Subtitle cue source binding 无效")
        units = [source[uid] for uid in cue["source_unit_ids"]]
        start = Decimal(cue["in_seconds"]); end = Decimal(cue["out_seconds"])
        if start != Decimal(units[0]["media_start_seconds"]) or end != Decimal(units[-1]["media_end_seconds"]):
            raise SubtitleArtifactError("Subtitle timing 不是 Timed Transcript 边界")
        if start < previous or start >= end or end > duration:
            raise SubtitleArtifactError("Subtitle timing 非单调或超出 Clean A-roll")
        precision = "segment" if transcript["timestamp_granularity"] == "segment" else "word"
        if cue["timing_precision"] != precision or (precision == "segment" and len(units) != 1):
            raise SubtitleArtifactError("segment-only 字幕伪造了 word precision")
        if cue["text"] != normalize_subtitle_text("".join(str(unit["spoken_text"]) for unit in units)):
            raise SubtitleArtifactError("Subtitle text 不可从 Transcript 重建")
        if len(cue["text"]) > int(profile["max_lines"]) * int(profile["max_chars_per_line"]):
            raise SubtitleArtifactError("Subtitle cue 超过两行确定性容量")
        previous = end
    if not artifact["cues"] or artifact.get("artifact_digest") != _digest(artifact):
        raise SubtitleArtifactError("Subtitle Artifact digest 或 cues 无效")
