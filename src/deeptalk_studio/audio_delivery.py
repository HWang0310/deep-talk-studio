"""Audio-only final-delivery projection for DeepTalk Studio.

A final, approved local narration WAV/MP3 (human-recorded or externally
AI-generated, provenance declared by the owner) owns the real timeline.  This
module wires the existing canonical chain (media import -> ASR -> alignment ->
semantic timeline) to the formal Asset Pack + Edit Map delivery without
pretending there is a human-camera A-roll.

Deterministic mapping rules (fail closed, never auto-pick):
- one semantic span (one reviewed Script beat) maps to exactly one cue, or to
  no cue at all; multiple cues on one beat cannot be projected one-to-one and
  become an explicit VISUAL_GAP instead of picking one silently.
- a ready local material is used only when it is bound to exactly one cue of
  that span and is file/SHA/production/rights-verified; multiple ready
  candidates for the same cue are a VISUAL_GAP (no auto-winner).
- FACT_CONFLICT and low-confidence spans are keep_only and become VISUAL_GAP.

Rights boundary (canonical Rights/Reuse contract): `production_status=ready`
only proves local file integrity (the material bridge deliberately keeps
`rights_reuse_affects_production_gate=False`), never reuse authorization.
Only materials whose validated `rights_status` is one of the canonical
`SAFE_REUSE_STATUSES` (public_domain / explicit_reuse_allowed /
creative_commons / official_press_asset) with inspected provenance and
ready_to_use eligibility may enter the Asset Pack; unknown,
permission-required, editorial-reference-only and avoid materials become an
AUDIO_ONLY visual gap with the reason recorded, and never enter the manifest.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .asset_pack_workflow import build_production_asset_pack
from .fact_conflict import detect_fact_conflicts
from .material_schema import SAFE_REUSE_STATUSES
from .semantic_timeline import build_semantic_timeline


class AudioDeliveryError(ValueError):
    """Audio-only delivery cannot truthfully produce an Asset Pack / Edit Map."""


AUDIO_ONLY = "AUDIO_ONLY"
REAL_MATERIAL = "REAL_MATERIAL"


def _data(value):
    return value.data if hasattr(value, "data") else value


def _digest(value: Mapping) -> str:
    payload = deepcopy(dict(value)); payload.pop("plan_digest", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _verified_local(item: Mapping) -> bool:
    path = Path(str(item.get("local_path", "")))
    if path.is_symlink() or not path.is_file():
        return False
    if path.stat().st_size != int(item.get("byte_size", -1)):
        return False
    if hashlib.sha256(path.read_bytes()).hexdigest() != str(item.get("sha256", "")):
        return False
    return True


def build_approved_facts(report_data: Mapping, script: Mapping) -> list[dict]:
    """Deterministic, review-bound approved facts for the conflict detector.

    Only claims already confirmed in the approved Research and actually bound
    to a beat through the reviewed Script enter the conflict check.  An empty
    result is a real conclusion (nothing bound), never an automatic pass.
    """
    claims = {str(item.get("id", "")): item for item in report_data.get("claims", []) if isinstance(item, Mapping)}
    facts: list[dict] = []
    for beat in script.get("beats", []):
        beat_id = str(beat.get("beat_id", ""))
        for claim_id in beat.get("claim_ids", []) or []:
            claim = claims.get(str(claim_id))
            if not claim or claim.get("classification") != "confirmed_fact":
                continue
            text = str(claim.get("claim", "")).strip()
            if "年" in text and any(ch.isdigit() for ch in text):
                facts.append({
                    "kind": "date",
                    "value": "".join(text.split()),
                    "beat_id": beat_id,
                    "claim_id": str(claim_id),
                    "approved_value": "".join(text.split()),
                    "spoken_value": "",
                })
    return facts


def _gap_reason(span: Mapping) -> str:
    if span.get("reason") == "FACT_CONFLICT":
        return "FACT_CONFLICT：口播与已批准事实冲突，禁止展示任何相关画面。"
    if span.get("visual_eligibility") != "safe":
        return "该段真实对齐不可靠或存在事实冲突，禁止自动分配画面。"
    if span.get("alignment_status") != "aligned":
        return "该段对齐状态不满足安全视觉要求。"
    return "无合规素材且无真人画面可保留，需要人工补画面。"


def derive_audio_assets(
    script: Mapping,
    alignment: Mapping,
    fact_conflicts: Sequence[Mapping],
    material_view: Mapping,
    *,
    timeline_id: str,
    created_at: str,
    clean_aroll_gate_status: str,
) -> dict:
    """Project semantic timeline + visual opportunities + candidate assets.

    Returns a dict: roots, timeline, visual_plan, candidates, gaps, span_to_cue.
    The visual plan is a visual-director-plan/1-compatible projection with a
    deterministic span_id on every opportunity and is fully re-derivable.

    `clean_aroll_gate_status` must be the controlled result of the real Clean
    A-roll Gate on this media+transcript; it is bound into the delivery roots
    and can never be hardcoded by a caller.
    """
    script = _data(script)
    # the alignment artifact itself is produced by the real audio chain; the
    # semantic-timeline contract requires an explicit provenance marker, so we
    # inject it on a read-only copy (artifact digest stays the original).
    alignment = dict(alignment)
    alignment.setdefault("timing_provenance", "actual_aroll_alignment")
    timeline = build_semantic_timeline(
        script, alignment, list(fact_conflicts),
        timeline_id=timeline_id, created_at=created_at,
    )
    spans = list(timeline["spans"])
    spans_by_id = {str(item["span_id"]): item for item in spans}
    blocked = {str(item.get("beat_id", "")) for item in fact_conflicts if item.get("display_blocked")}
    cue_by_id = {str(item.get("cue_id", "")): item for item in alignment.get("cue_timeline", [])}

    # ready local material candidates bound to exactly one cue.  Rights are
    # verified here (not by the material bridge): only canonical safe-reuse
    # statuses with inspected provenance and ready_to_use eligibility pass;
    # everything else is recorded as a rights-blocked visual gap instead of an
    # automatic asset.
    by_cue: dict[str, list[dict]] = {}
    rights_blocked_by_cue: dict[str, list[dict]] = {}
    for item in material_view.get("items", []):
        if item.get("source_kind") != "material":
            continue
        if item.get("production_status") != "ready" or item.get("provenance_status") != "inspected":
            continue
        if item.get("asset_type") == "video_clip_reference":
            ref = item.get("video_reference", {}) or {}
            try:
                clip_start = float(ref.get("start_seconds", 0)); clip_end = float(ref.get("end_seconds", 0))
            except (TypeError, ValueError):
                clip_start = clip_end = 0.0
            if clip_end <= clip_start:
                # a reference clip without a chosen segment is not a usable asset
                continue
        cue_ids = [str(c) for c in item.get("cue_ids", []) if str(c).strip()]
        if len(cue_ids) != 1 or cue_ids[0] not in cue_by_id:
            continue
        if not _verified_local(item):
            continue
        if item.get("rights_status") not in SAFE_REUSE_STATUSES or item.get("historical_eligibility_status") != "ready_to_use":
            rights_blocked_by_cue.setdefault(cue_ids[0], []).append(item)
            continue
        by_cue.setdefault(cue_ids[0], []).append(item)

    span_to_cue: dict[str, str] = {}
    gaps: list[dict] = []
    for span in spans:
        beat_id = str(span["beat_id"]); span_id = str(span["span_id"])
        beat_cues = [
            item for item in alignment.get("cue_timeline", [])
            if str(item.get("beat_id", "")) == beat_id and str(item.get("actual_start_seconds", "")).strip()
        ]
        if len(beat_cues) != 1:
            span_to_cue[span_id] = ""
            gaps.append({
                "span_id": span_id, "beat_id": beat_id, "reason": "multiple_or_missing_cues",
                "detail": "该语义段对应 0 个或多个 cue，无法一一映射，禁止自动挑选。",
            })
            continue
        cue_id = str(beat_cues[0]["cue_id"])
        if cue_id in span_to_cue.values():
            span_to_cue[span_id] = ""
            gaps.append({
                "span_id": span_id, "beat_id": beat_id, "reason": "cue_span_conflict",
                "detail": "同一 cue 被多个 span 引用，无法一一映射。",
            })
            continue
        span_to_cue[span_id] = cue_id

    opportunities: list[dict] = []
    candidates: list[dict] = []
    for index, span in enumerate(spans, 1):
        span_id = str(span["span_id"]); beat_id = str(span.get("beat_id", ""))
        cue_id = span_to_cue.get(span_id, "")
        opportunity_id = f"OP{index:03d}"
        decision = AUDIO_ONLY
        why = "该时间段无真人画面可保留，需要人工补画面。"
        asset_candidate = None
        if beat_id in blocked or span.get("visual_eligibility") != "safe":
            why = _gap_reason(span)
        elif cue_id:
            owned = by_cue.get(cue_id, [])
            if not owned:
                if rights_blocked_by_cue.get(cue_id):
                    why = "该时间段的候选素材没有可核验的复用授权（未知、需授权或仅可参考），不能自动使用，需要人工补画面或先取得授权。"
                else:
                    why = "该时间段没有通过权利/文件校验的合规素材，需要人工补画面。"
            elif len(owned) > 1:
                why = "该时间段存在多个可复用素材候选，无法自动挑选，需要人工决定。"
            else:
                item = owned[0]
                decision = REAL_MATERIAL
                clip_hint = ""
                if item.get("asset_type") == "video_clip_reference":
                    ref = item.get("video_reference", {}) or {}
                    try:
                        clip_start = float(ref.get("start_seconds", 0)); clip_end = float(ref.get("end_seconds", 0))
                    except (TypeError, ValueError):
                        clip_start = clip_end = 0.0
                    if clip_end > clip_start:
                        clip_hint = f"，使用该素材片段 {clip_start:.2f}–{clip_end:.2f} 秒"
                asset_candidate = {
                    "opportunity_id": opportunity_id,
                    "asset_class": REAL_MATERIAL,
                    "qa_status": "ready",
                    "filename": Path(str(item["local_path"])).name,
                    "local_path": str(item["local_path"]),
                    "byte_size": int(item["byte_size"]),
                    "sha256": str(item["sha256"]),
                    "provenance": str(item.get("rights_basis", "")) or str(item.get("source_url", "")),
                    "placement_advice": f"按真实时间放入对应位置{clip_hint}。",
                }
                why = str(item.get("caption", "")) or "证据素材。"
        cue = cue_by_id.get(cue_id)
        time_range = (
            {"start_seconds": str(cue["actual_start_seconds"]), "end_seconds": str(cue["actual_end_seconds"])}
            if cue and str(cue.get("actual_start_seconds", "")).strip() else
            {"start_seconds": str(span["actual_start_seconds"]), "end_seconds": str(span["actual_end_seconds"])}
        )
        if asset_candidate is not None:
            candidates.append(asset_candidate)
        opportunities.append({
            "opportunity_id": opportunity_id,
            "span_id": span_id,
            "cue_id": cue_id,
            "source_time_range": time_range,
            "visual_intent": "证据/解释画面" if decision == REAL_MATERIAL else "无画面（需人工补画）",
            "why_visual": why,
            "decision": decision,
            "importance": "supporting",
            "review_requirement": "not_needed",
            "risk_flags": ["audio_only_no_human_frame"] if decision == AUDIO_ONLY else [],
            "alignment_digest": str(alignment.get("artifact_digest", "")),
            "status": "keep" if decision == AUDIO_ONLY else "proposed",
        })
    visual_plan = {
        "artifact_version": "visual-director-plan/1",
        "plan_id": f"VP-AUDIO-{timeline_id}",
        "revision": 1,
        "previous_revision": 0,
        "created_at": created_at,
        "alignment_digest": str(alignment.get("artifact_digest", "")),
        "opportunities": opportunities,
    }
    visual_plan["plan_digest"] = _digest(visual_plan)
    return {
        "roots": {
            "alignment_digest": str(alignment.get("artifact_digest", "")),
            "transcript_digest": str(timeline.get("transcript_digest", "")),
            "timing_provenance": "actual_aroll_alignment",
            "clean_aroll_gate_status": clean_aroll_gate_status,
        },
        "timeline": timeline,
        "visual_plan": visual_plan,
        "candidates": candidates,
        "gaps": gaps,
        "span_to_cue": span_to_cue,
    }


def run_audio_only_delivery(
    inputs,
    provider,
    *,
    clock,
    id_factory,
):
    """Concrete audio-only chain ending in Asset Pack + Edit Map.

    Reuses the existing narration/ASR/alignment chain, runs the formal Clean
    A-roll Gate on the real transcript, then adds the formal semantic-timeline
    -> visual-plan -> Asset Pack delivery.  No preview is rendered, no A-roll
    frame is manufactured.
    """
    from .alignment_builder import build_script_alignment
    from .alignment_profile import load_alignment_profile
    from .alignment_storage import save_script_alignment
    from .audio_timestamp_mapping import derive_timestamp_mapping, validate_timestamp_mapping
    from .edit_bridge_planner import (
        build_base_aroll_placement, build_edit_bridge, build_visual_placements, derive_placement_timing,
    )
    from .edit_bridge_qa import build_audio_delivery_qa_inputs, run_audio_edit_bridge_qa
    from .material_bridge import build_material_production_view
    from .material_profile import load_material_profile
    from .narration_media import audio_extraction_profile, extract_transcription_audio, import_narration_media, canonical_digest
    from .narration_storage import NarrationBundle, save_narration_bundle
    from .rough_cut_profile import load_aligned_preview_profile, load_rough_cut_profile
    from .subtitle_builder import build_subtitle_artifact
    from .subtitle_profile import load_subtitle_profile
    from .subtitle_storage import save_subtitle_artifact
    from .transcript_builder import build_timed_transcript, validate_timed_transcript
    from .transcription_chunking import load_transcription_chunk_profile, plan_transcription_chunks, validate_transcription_chunk_plan

    root = Path(inputs.output_root).resolve()
    if root.exists():
        raise AudioDeliveryError("本次音频对齐输出已经存在，不会覆盖；请使用新的试用目录")
    now = clock()
    media_result = import_narration_media(inputs.clean_aroll_path, root / "narration-media", imported_at=now, id_factory=id_factory)
    media = media_result.artifact
    if media["media_kind"] != "audio" or media["video_stream"]["present"]:
        raise AudioDeliveryError("audio 交付只接受不含视频流的纯音频媒体")
    preferred_sample_rate = getattr(provider, "preferred_sample_rate", 48000)
    extraction_profile = audio_extraction_profile(sample_rate=preferred_sample_rate)
    extracted_result = extract_transcription_audio(media, root / "derived" / "transcription.wav", profile=extraction_profile, created_at=now)
    extracted = extracted_result.artifact
    mapping = derive_timestamp_mapping(media, extracted, mapping_id=id_factory("MAPPING"), created_at=now)
    validate_timestamp_mapping(mapping, media, extracted)
    chunk_profile_path = getattr(provider, "chunk_profile_path", None)
    chunk_profile = load_transcription_chunk_profile(chunk_profile_path) if chunk_profile_path else load_transcription_chunk_profile()
    chunk_plan = plan_transcription_chunks(extracted, mapping, chunk_profile)
    validate_transcription_chunk_plan(chunk_plan, extracted, mapping, chunk_profile)
    configured_model = getattr(provider, "default_configured_model", "whisper-1")
    provider_result = provider.transcribe(extracted, chunk_plan, "zh", configured_model)
    transcript = build_timed_transcript(provider_result, media, extracted, mapping, chunk_plan, transcript_id=id_factory("TRANSCRIPT"), created_at=now)
    validate_timed_transcript(transcript, media, extracted, mapping, chunk_plan)
    # Formal Clean A-roll Gate on the real transcript (same retake/complete-run
    # detection as the human branch).  A needs_manual_cleanup result blocks the
    # delivery with the gate's own owner-facing message; the controlled result
    # is bound into the delivery roots and can never be hardcoded.
    from .clean_aroll_gate import inspect_clean_aroll
    gate = inspect_clean_aroll(media, transcript)
    if gate.status != "accepted":
        raise AudioDeliveryError(gate.user_message)
    subtitle_profile = load_subtitle_profile()
    subtitle = build_subtitle_artifact(transcript, media, subtitle_profile, subtitle_id=id_factory("SUBTITLE"), created_at=now)
    material_profile = load_material_profile()
    material_view = build_material_production_view(
        inputs.material_package_path, inputs.script, inputs.report, material_profile,
        inputs.material_asset_root, artifact_resolver=inputs.artifact_resolver,
    )
    material_package = json.loads(inputs.material_package_path.read_text(encoding="utf-8"))
    cues = material_package["cue_sheet"]
    alignment_profile = load_alignment_profile()
    alignment = build_script_alignment(inputs.script, transcript, mapping, alignment_profile, cues, alignment_id=id_factory("ALIGNMENT"), created_at=now, media=media)
    rough_profile = load_rough_cut_profile(material_profile); preview_profile = load_aligned_preview_profile()
    allowed_roots = tuple(Path(path).resolve() for path in inputs.allowed_roots) + (root,)
    # placements/timing reuse the canonical chain so QA re-derivation is strong
    raw_placements = build_visual_placements(
        alignment, material_view, inputs.production_plan, inputs.motion_manifest,
        media, allowed_roots, inputs.production_qa,
        artifact_resolver=inputs.artifact_resolver,
    )
    timing_profiles = (rough_profile, preview_profile, media["presentation_duration_seconds"])
    timing = derive_placement_timing(raw_placements, timing_profiles)

    report_digest = canonical_digest(inputs.report.data)
    bindings = {
        "narration_media_digest": media["artifact_digest"], "extracted_audio_digest": extracted["artifact_digest"],
        "timestamp_mapping_digest": mapping["mapping_digest"], "chunk_plan_digest": chunk_plan.digest,
        "transcript_digest": transcript["transcript_digest"], "script_content_digest": alignment["script_content_digest"],
        "research_digest": report_digest, "material_package_digest": material_view["package_digest"],
        "material_view_digest": material_view["view_digest"], "production_plan_digest": inputs.production_plan["plan_digest"],
        "motion_manifest_digest": inputs.motion_manifest["manifest_digest"], "production_qa_digest": inputs.production_qa["qa_digest"],
        "alignment_digest": alignment["artifact_digest"], "alignment_profile_digest": alignment_profile["profile_digest"],
        "rough_cut_profile_digest": rough_profile["profile_digest"], "aligned_preview_profile_digest": preview_profile["profile_digest"],
        "subtitle_artifact_digest": subtitle["artifact_digest"], "subtitle_profile_digest": subtitle_profile["profile_digest"],
    }
    bridge = build_edit_bridge(bindings, timing.placements, timing.conflicts, timing.adjustments, alignment["gaps"], bridge_id=id_factory("BRIDGE"), created_at=now)

    approved_facts = build_approved_facts(inputs.report.data, _data(inputs.script))
    fact_conflicts = detect_fact_conflicts(_data(inputs.script), transcript, alignment, approved_facts)
    delivery = derive_audio_assets(
        _data(inputs.script), alignment, fact_conflicts, material_view,
        timeline_id=id_factory("TIMELINE"), created_at=now,
        clean_aroll_gate_status=gate.status,
    )
    episode_root = root / "episode"
    pack = build_production_asset_pack(
        delivery["roots"], delivery["timeline"]["spans"], delivery["visual_plan"],
        delivery["candidates"], episode_root=episode_root, created_at=now,
    )
    # 05_A-roll/: real-time lineage artifacts, read-only copies
    aroll_dir = episode_root / "05_A-roll"; aroll_dir.mkdir(parents=True, exist_ok=True)
    for source, name in (
        (transcript, "actual-transcript.json"),
        (alignment, "alignment.json"),
        (delivery["timeline"], "semantic-timeline.json"),
        (gate.to_dict(), "clean-aroll-gate.json"),
    ):
        (aroll_dir / name).write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    narration_paths = save_narration_bundle(NarrationBundle(media, extracted, mapping, transcript), root / "artifacts")
    alignment_paths = save_script_alignment(alignment, root / "alignment")
    subtitle_paths = save_subtitle_artifact(subtitle, root / "subtitles")

    qa_inputs = build_audio_delivery_qa_inputs(
        media, extracted, mapping, chunk_plan, chunk_profile, transcript,
        subtitle, subtitle_profile, inputs, alignment, alignment_profile, cues,
        material_view, timing, rough_profile, preview_profile, bridge, delivery, pack, episode_root, allowed_roots,
        gate=gate,
    )
    qa = run_audio_edit_bridge_qa(qa_inputs)
    if qa["package_gate_status"] == "fail":
        raise AudioDeliveryError("正式 Audio Asset Pack QA 未通过")
    qa_path = root / "delivery" / "audio-delivery-qa.json"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "media": media, "extracted": extracted, "mapping": mapping, "transcript": transcript,
        "subtitle": subtitle, "alignment": alignment, "delivery": delivery,
        "asset_pack": pack, "qa": qa, "qa_path": qa_path, "preview_path": None,
        "qa_context": getattr(qa_inputs, "context", None),
        "paths": {
            "markdown": pack.markdown_path, "csv": pack.csv_path,
            "json": pack.json_path, "manifest": pack.manifest_path,
            "qa": qa_path, "narration": narration_paths,
        },
    }


__all__ = [
    "AudioDeliveryError",
    "AUDIO_ONLY",
    "REAL_MATERIAL",
    "build_approved_facts",
    "derive_audio_assets",
    "run_audio_only_delivery",
]