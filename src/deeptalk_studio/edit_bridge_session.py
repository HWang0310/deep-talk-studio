"""Resolve approved upstream artifacts and run one concrete aligned-edit session."""

import json
from dataclasses import dataclass,replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .models import ResearchReport, ScriptDraft


class RealEditBridgeSessionError(ValueError):
    """An ordinary session cannot be resolved safely and uniquely."""


@dataclass(frozen=True)
class RealEditBridgeSessionInputs:
    session_root: Path
    clean_aroll_path: Path
    report: ResearchReport
    script: ScriptDraft
    material_package_path: Path
    production_plan: Mapping[str, Any]
    motion_manifest: Mapping[str, Any]
    production_qa: Mapping[str, Any]
    material_asset_root: Path
    allowed_roots: Sequence[Path]
    output_root: Path


@dataclass(frozen=True)
class RealEditBridgeSessionResult:
    artifacts: Mapping[str, Any]
    paths: Mapping[str, Path]
    preview_path: Path
    qa: Mapping[str, Any]


def _json(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RealEditBridgeSessionError(f"无法读取正式工件：{path.name}") from exc
    if not isinstance(value, dict):
        raise RealEditBridgeSessionError(f"正式工件不是对象：{path.name}")
    return value


def _newest(paths, predicate, label):
    candidates = []
    for path in paths:
        try:
            value = _json(path)
        except RealEditBridgeSessionError:
            continue
        if predicate(value):
            candidates.append((path.stat().st_mtime_ns, str(path), path, value))
    if not candidates:
        raise RealEditBridgeSessionError(f"没有找到可用的{label}")
    candidates.sort()
    return candidates[-1][2], candidates[-1][3]


def resolve_real_edit_bridge_session(session_root, repo_root=None):
    """Find one user video and its newest matching approved canonical roots."""
    from .material_profile import load_material_profile
    from .material_storage import load_material_package
    from .production_qa import validate_motion_manifest, validate_production_qa
    from .script_profile import load_script_profile
    from .script_storage import load_script
    from .validation import validate_report

    session = Path(session_root).resolve()
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    videos = [
        path for path in session.iterdir()
        if path.is_file() and not path.is_symlink() and path.suffix.casefold() in {".mp4", ".mov", ".m4v"}
    ] if session.is_dir() else []
    if len(videos) != 1:
        raise RealEditBridgeSessionError("请只放入一个已经剪好口气的真人口播视频")
    production_path, plan = _newest(
        (root / "production_packages").rglob("production-plan-r*.json"),
        lambda value: (
            value.get("qa_state", {}).get("state") if isinstance(value.get("qa_state"), dict)
            else value.get("qa_state")
        ) in {"pass", "warnings", "not_run"},
        "Production Plan",
    )
    production_dir = production_path.parent
    manifest_path, manifest = _newest(
        production_dir.glob("motion-asset-manifest-r*.json"),
        lambda value: value.get("production_plan_digest") == plan.get("plan_digest"),
        "Motion Manifest",
    )
    _, production_qa = _newest(
        production_dir.glob("production-qa-r*.json"),
        lambda value: value.get("production_plan_digest") == plan.get("plan_digest"),
        "Production QA",
    )
    validate_motion_manifest(manifest, plan)
    validate_production_qa(production_qa, plan, manifest)
    # Production 0.6 does not carry report_id. Bind via reviewed Script first,
    # then resolve its exact report identity/revision.
    script_path, script_data = _newest(
        (root / "script_drafts").rglob("script-draft-r*.json"),
        lambda value: value.get("script_id") == plan.get("script_id")
        and value.get("revision") == plan.get("script_revision")
        and value.get("status") == "reviewed",
        "已审查 Script",
    )
    report_path, report_data = _newest(
        (root / "reports").rglob("research-report-r*.json"),
        lambda value: value.get("report_id") == script_data.get("report_id")
        and value.get("revision") == script_data.get("report_revision")
        and value.get("status") == "ready_for_script",
        "与 Script 精确绑定的 Research",
    )
    report = ResearchReport.from_dict(report_data); validate_report(report)
    script = load_script(script_path, report, load_script_profile())
    material_path, _ = _newest(
        (root / "material_packages").rglob("material-package-r*.json"),
        lambda value: value.get("package_id") == plan.get("material_package_id")
        and value.get("revision") == plan.get("material_package_revision")
        and value.get("status") in {"reviewed", "reviewed_with_warnings"},
        "已审查 Material Package",
    )
    load_material_package(material_path, script, report, load_material_profile())
    material_asset_root = root / "material_assets" / str(plan["material_package_id"])
    output_root = session / "DeepTalk-Aligned-Edit"
    return RealEditBridgeSessionInputs(
        session, videos[0], report, script, material_path, plan, manifest, production_qa,
        material_asset_root,
        (material_asset_root, root / "production_assets", output_root, session),
        output_root,
    )


def run_real_edit_bridge_session(
    inputs: RealEditBridgeSessionInputs,
    provider,
    *,
    clock: Callable[[], str],
    id_factory: Callable[[str], str],
    renderer=None,
):
    """Concrete Tasks 3–26 owner. No stage lambdas or caller-owned QA."""
    from .aligned_preview.remotion import (
        RemotionAlignedPreviewRenderer, build_aligned_preview_manifest,
        mux_clean_aroll_audio,
    )
    from .alignment_builder import build_script_alignment
    from .alignment_profile import load_alignment_profile
    from .alignment_storage import save_script_alignment
    from .audio_timestamp_mapping import derive_timestamp_mapping, validate_timestamp_mapping
    from .edit_bridge_planner import build_edit_bridge, build_visual_placements, derive_placement_timing
    from .edit_bridge_qa import CanonicalEditBridgeQAContext, run_canonical_edit_bridge_qa
    from .edit_bridge_storage import save_edit_bridge
    from .edit_bridge_validation import validate_edit_bridge
    from .material_bridge import build_material_production_view
    from .material_profile import load_material_profile
    from .narration_media import audio_extraction_profile, extract_transcription_audio, import_narration_media, canonical_digest
    from .narration_storage import NarrationBundle, save_narration_bundle
    from .rough_cut_profile import load_aligned_preview_profile, load_rough_cut_profile
    from .transcript_builder import build_timed_transcript, validate_timed_transcript
    from .transcription_chunking import load_transcription_chunk_profile, plan_transcription_chunks, validate_transcription_chunk_plan
    from .subtitle_builder import build_subtitle_artifact
    from .subtitle_profile import load_subtitle_profile
    from .subtitle_storage import save_subtitle_artifact

    root = Path(inputs.output_root).resolve()
    if root.exists():
        raise RealEditBridgeSessionError("本次对齐输出已经存在，不会覆盖；请使用新的试用目录")
    now = clock(); renderer = renderer or RemotionAlignedPreviewRenderer()
    media_result = import_narration_media(inputs.clean_aroll_path, root / "narration-media", imported_at=now, id_factory=id_factory)
    media = media_result.artifact
    if media["media_kind"] != "video":
        raise RealEditBridgeSessionError("这一阶段需要真人口播视频，不接受纯音频")
    extraction_profile = audio_extraction_profile()
    extracted_result = extract_transcription_audio(media, root / "derived" / "transcription.wav", profile=extraction_profile, created_at=now)
    extracted = extracted_result.artifact
    mapping = derive_timestamp_mapping(media, extracted, mapping_id=id_factory("MAPPING"), created_at=now)
    validate_timestamp_mapping(mapping, media, extracted)
    chunk_profile = load_transcription_chunk_profile()
    chunk_plan = plan_transcription_chunks(extracted, mapping, chunk_profile)
    validate_transcription_chunk_plan(chunk_plan, extracted, mapping, chunk_profile)
    provider_result = provider.transcribe(extracted, chunk_plan, "zh", "whisper-1")
    transcript = build_timed_transcript(provider_result, media, extracted, mapping, chunk_plan, transcript_id=id_factory("TRANSCRIPT"), created_at=now)
    validate_timed_transcript(transcript, media, extracted, mapping, chunk_plan)
    subtitle_profile = load_subtitle_profile()
    subtitle = build_subtitle_artifact(transcript, media, subtitle_profile, subtitle_id=id_factory("SUBTITLE"), created_at=now)
    material_profile = load_material_profile()
    material_view = build_material_production_view(inputs.material_package_path, inputs.script, inputs.report, material_profile, inputs.material_asset_root)
    material_package = json.loads(inputs.material_package_path.read_text(encoding="utf-8"))
    cues = material_package["cue_sheet"]
    alignment_profile = load_alignment_profile()
    alignment = build_script_alignment(inputs.script, transcript, mapping, alignment_profile, cues, alignment_id=id_factory("ALIGNMENT"), created_at=now, media=media)
    rough_profile = load_rough_cut_profile(material_profile); preview_profile = load_aligned_preview_profile()
    allowed_roots = tuple(Path(path).resolve() for path in inputs.allowed_roots) + (root,)
    raw_placements = build_visual_placements(alignment, material_view, inputs.production_plan, inputs.motion_manifest, media, allowed_roots, inputs.production_qa)
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
    validate_edit_bridge(bridge, bindings, timing.placements, timing.conflicts, timing.adjustments, alignment["gaps"])
    project = renderer.prepare_project(bridge, media, subtitle, subtitle_profile, allowed_roots, root / "preview-projects")
    renderer.validate_project(project)
    visual = renderer.render_visual(project, root / "outputs" / "ALIGNED_PREVIEW_VISUAL.mp4")
    preview_path = root / "outputs" / "ALIGNED_PREVIEW.mp4"
    mux = mux_clean_aroll_audio(visual.output_path, media, preview_path)
    preview_manifest = build_aligned_preview_manifest(preview_path, bridge, preview_profile, media, project.staged_placement_ids, subtitle, subtitle_profile, project.subtitles_enabled)
    context = CanonicalEditBridgeQAContext(
        media, extracted, mapping, chunk_plan, chunk_profile, transcript,
        inputs.script, alignment_profile, cues, alignment,
        material_view, inputs.material_package_path, inputs.report, material_profile, inputs.material_asset_root,
        inputs.production_plan, inputs.motion_manifest, inputs.production_qa,
        timing.placements, timing_profiles, timing, bridge,
        preview_profile, preview_manifest, preview_path, project.staged_placement_ids,
        allowed_roots, project, renderer,
    )
    context = replace(context, subtitle_artifact=subtitle, subtitle_profile=subtitle_profile)
    qa = run_canonical_edit_bridge_qa(context)
    if qa["package_gate_status"] == "fail":
        raise RealEditBridgeSessionError("正式 Edit Bridge QA 未通过")
    paths = {}
    narration_paths = save_narration_bundle(NarrationBundle(media, extracted, mapping, transcript), root / "artifacts")
    paths.update(media=narration_paths.media, extracted=narration_paths.extracted_audio, mapping=narration_paths.mapping, transcript=narration_paths.transcript)
    alignment_paths = save_script_alignment(alignment, root / "alignment"); paths.update(alignment=alignment_paths.json_path)
    subtitle_paths = save_subtitle_artifact(subtitle, root / "subtitles"); paths.update(subtitle=subtitle_paths.json, subtitle_srt=subtitle_paths.srt)
    bridge_paths = save_edit_bridge(bridge, root / "bridge"); paths.update(bridge=bridge_paths.json_path, markers=bridge_paths.csv_path)
    manifest_path = root / "outputs" / "aligned-preview-manifest.json"; manifest_path.write_text(json.dumps(preview_manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    qa_path = root / "outputs" / "edit-bridge-qa.json"; qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    paths.update(preview_manifest=manifest_path, qa=qa_path, preview=preview_path)
    artifacts = {"media":media,"extracted":extracted,"mapping":mapping,"chunk_plan":chunk_plan,"transcript":transcript,"subtitle":subtitle,"subtitle_profile":subtitle_profile,"alignment":alignment,"material_view":material_view,"timing":timing,"bridge":bridge,"preview_manifest":preview_manifest,"mux":mux,"qa_context":context}
    return RealEditBridgeSessionResult(artifacts, paths, preview_path, qa)


def load_real_edit_bridge_session_result(session_root, *, renderer=None):
    """Rehydrate a finished session for an ordinary-language immutable revision."""
    from .aligned_preview.remotion import RemotionAlignedPreviewRenderer
    from .alignment_profile import load_alignment_profile
    from .alignment_storage import load_script_alignment
    from .edit_bridge_planner import build_visual_placements,derive_placement_timing
    from .edit_bridge_qa import CanonicalEditBridgeQAContext
    from .edit_bridge_storage import load_edit_bridge
    from .material_bridge import build_material_production_view
    from .material_profile import load_material_profile
    from .narration_storage import load_narration_bundle
    from .rough_cut_profile import load_aligned_preview_profile,load_rough_cut_profile
    from .transcription_chunking import load_transcription_chunk_profile,plan_transcription_chunks
    from .subtitle_profile import load_subtitle_profile
    from .subtitle_storage import load_subtitle_artifact
    session=Path(session_root).resolve();root=session/"DeepTalk-Aligned-Edit"
    if not root.is_dir():raise RealEditBridgeSessionError("还没有可以修改的对齐粗剪")
    inputs=resolve_real_edit_bridge_session(session);bundle=load_narration_bundle(next((root/"artifacts").rglob("narration-media.json")))
    if not all((bundle.extracted_audio,bundle.mapping,bundle.transcript)):raise RealEditBridgeSessionError("上一轮时间工件不完整")
    subtitle_profile=load_subtitle_profile();subtitle=load_subtitle_artifact(root/"subtitles"/"subtitle-r0001.json",bundle.transcript,bundle.media,subtitle_profile)
    chunk_profile=load_transcription_chunk_profile();chunk_plan=plan_transcription_chunks(bundle.extracted_audio,bundle.mapping,chunk_profile)
    alignment=load_script_alignment(sorted((root/"alignment").rglob("script-alignment-r*.json"))[-1])
    material_profile=load_material_profile();material_view=build_material_production_view(inputs.material_package_path,inputs.script,inputs.report,material_profile,inputs.material_asset_root)
    material_package=_json(inputs.material_package_path);cues=material_package["cue_sheet"];alignment_profile=load_alignment_profile()
    rough=load_rough_cut_profile(material_profile);preview_profile=load_aligned_preview_profile();timing_profiles=(rough,preview_profile,bundle.media["presentation_duration_seconds"])
    allowed=tuple(Path(path).resolve() for path in inputs.allowed_roots)+(root,)
    raw=build_visual_placements(alignment,material_view,inputs.production_plan,inputs.motion_manifest,bundle.media,allowed,inputs.production_qa);timing=derive_placement_timing(raw,timing_profiles)
    bridge=load_edit_bridge(sorted((root/"bridge").rglob("edit-bridge-r*.json"))[-1]);preview_path=root/"outputs"/"ALIGNED_PREVIEW.mp4"
    revised_previews=sorted((root/"outputs").glob("ALIGNED_PREVIEW-r*.mp4"))
    if revised_previews:preview_path=revised_previews[-1]
    revision=int(bridge["revision"])
    manifest_path=(root/"outputs"/"aligned-preview-manifest.json") if revision==1 else (root/"outputs"/f"aligned-preview-manifest-r{revision:04d}.json")
    qa_path=(root/"outputs"/"edit-bridge-qa.json") if revision==1 else (root/"outputs"/f"edit-bridge-qa-r{revision:04d}.json")
    manifest=_json(manifest_path);qa=_json(qa_path)
    context=CanonicalEditBridgeQAContext(bundle.media,bundle.extracted_audio,bundle.mapping,chunk_plan,chunk_profile,bundle.transcript,inputs.script,alignment_profile,cues,alignment,material_view,inputs.material_package_path,inputs.report,material_profile,inputs.material_asset_root,inputs.production_plan,inputs.motion_manifest,inputs.production_qa,tuple(bridge["visual_placements"]),timing_profiles,timing,bridge,preview_profile,manifest,preview_path,tuple(manifest["used_placement_ids"]),allowed,None,renderer or RemotionAlignedPreviewRenderer(),subtitle_artifact=subtitle,subtitle_profile=subtitle_profile)
    artifacts={"media":bundle.media,"extracted":bundle.extracted_audio,"mapping":bundle.mapping,"chunk_plan":chunk_plan,"transcript":bundle.transcript,"subtitle":subtitle,"subtitle_profile":subtitle_profile,"alignment":alignment,"material_view":material_view,"timing":timing,"bridge":bridge,"preview_manifest":manifest,"qa_context":context}
    return RealEditBridgeSessionResult(artifacts,{"bridge":sorted((root/"bridge").rglob("edit-bridge-r*.json"))[-1],"preview":preview_path},preview_path,qa)


def revise_real_edit_bridge_session(previous,feedback,*,clock,renderer=None):
    """Apply one uniquely resolved feedback and emit Bridge/Preview/QA revision."""
    from .aligned_preview.remotion import RemotionAlignedPreviewRenderer,build_aligned_preview_manifest,mux_clean_aroll_audio
    from .edit_bridge_qa import run_canonical_edit_bridge_qa
    from .edit_bridge_storage import create_bridge_revision,resolve_adjustment_target,save_edit_bridge
    resolution=resolve_adjustment_target(previous.artifacts["bridge"],feedback)
    if not resolution.unique:raise RealEditBridgeSessionError("这句话可能指向多个画面，请直接说出其中一个画面名称："+"、".join(resolution.candidates))
    context=previous.artifacts["qa_context"];selected=renderer or context.preview_renderer or RemotionAlignedPreviewRenderer();now=clock()
    revised=create_bridge_revision(previous.artifacts["bridge"],resolution.adjustment,created_at=now,fps=context.preview_profile["fps"])
    project=selected.prepare_project(revised,context.media,context.subtitle_artifact,context.subtitle_profile,context.allowed_roots,Path(previous.preview_path).parents[1]/"preview-projects")
    selected.validate_project(project);revision=revised["revision"];visual=selected.render_visual(project,Path(previous.preview_path).parent/f"ALIGNED_PREVIEW_VISUAL-r{revision:04d}.mp4")
    preview=Path(previous.preview_path).parent/f"ALIGNED_PREVIEW-r{revision:04d}.mp4";mux=mux_clean_aroll_audio(visual.output_path,context.media,preview)
    manifest=build_aligned_preview_manifest(preview,revised,context.preview_profile,context.media,project.staged_placement_ids,context.subtitle_artifact,context.subtitle_profile,project.subtitles_enabled)
    revised_context=replace(context,placements=tuple(revised["visual_placements"]),bridge=revised,preview_manifest=manifest,preview_path=preview,preview_used_placement_ids=project.staged_placement_ids,preview_project=project,preview_renderer=selected,previous_bridge=previous.artifacts["bridge"],revision_adjustment=resolution.adjustment)
    qa=run_canonical_edit_bridge_qa(revised_context)
    if qa["package_gate_status"]=="fail":raise RealEditBridgeSessionError("画面调整后的正式 QA 未通过")
    bridge_root=Path(previous.paths["bridge"]).parent.parent;bridge_paths=save_edit_bridge(revised,bridge_root)
    manifest_path=preview.parent/f"aligned-preview-manifest-r{revision:04d}.json";manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    qa_path=preview.parent/f"edit-bridge-qa-r{revision:04d}.json";qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    artifacts=dict(previous.artifacts);artifacts.update(bridge=revised,preview_manifest=manifest,mux=mux,qa_context=revised_context)
    return RealEditBridgeSessionResult(artifacts,{"bridge":bridge_paths.json_path,"preview":preview,"preview_manifest":manifest_path,"qa":qa_path},preview,qa)
