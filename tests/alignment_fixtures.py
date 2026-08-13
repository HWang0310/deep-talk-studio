from copy import deepcopy

from deeptalk_studio.alignment_profile import load_alignment_profile


NOW = "2026-08-13T10:00:00+08:00"


def script_fixture(granularity="word"):
    return {
        "script_id": "SCR-align",
        "revision": 1,
        "beats": [
            {"beat_id": "B001", "narration": "事件发生在八月九日。"},
            {"beat_id": "B002", "narration": "机构说问题来自流程故障。"},
            {"beat_id": "B003", "narration": "还有第三种选择。"},
        ],
    }


def transcript_fixture(*, granularity="word", duplicate_anchor=False, omit_second=False, risky=False):
    texts = ["事件发生在八月九日"]
    if not omit_second:
        texts.append("机构说问题来自流程故障")
    texts.append("还有第三种选择")
    if duplicate_anchor:
        texts.append("还有第三种选择")
    units = []
    cursor = 0
    for index, text in enumerate(texts):
        duration = len(text) / 4
        units.append({
            "unit_id": f"TU{index + 1:04d}", "order": index, "spoken_text": text,
            "media_start_seconds": str(cursor), "media_end_seconds": str(cursor + duration),
            "boundary_risk_ids": ["CBR-0001"] if risky and index == 1 else [],
        })
        cursor += duration
    risks = []
    if risky:
        risks = [{
            "risk_id": "CBR-0001", "risk_level": "high", "reason": "no_safe_pause_fallback",
            "media_guard_start_seconds": "2.0", "media_guard_end_seconds": "5.0",
        }]
    return {
        "artifact_version": "timed-transcript/1", "transcript_id": "TR-align",
        "transcript_digest": "t" * 64, "timestamp_granularity": granularity,
        "timed_units": units, "boundary_risks": risks,
        "transcription_chunk_plan_digest": "c" * 64,
        "narration_media_id": "NM-align", "narration_media_sha256": "m" * 64,
        "timestamp_mapping_id": "MAP-align", "timestamp_mapping_digest": "p" * 64,
    }


def mapping_fixture():
    return {"mapping_id": "MAP-align", "mapping_digest": "p" * 64}


def media_fixture(duration="30"):
    return {
        "media_id": "NM-align",
        "sha256": "m" * 64,
        "presentation_duration_seconds": duration,
    }


def cue_fixture():
    return [
        {"cue_id": "VC001", "beat_id": "B001", "placement_anchor": "事件发生"},
        {"cue_id": "VC002", "beat_id": "B003", "placement_anchor": "第三种选择"},
    ]


def profile_fixture():
    return deepcopy(load_alignment_profile())
