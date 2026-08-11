"""Deterministic Material Package → Production Plan 0.6 derivation."""

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Dict, Mapping

from .material_validation import material_package_digest
from .models import MaterialPackage, ResearchReport
from .production_profile import ProductionValidationError
from .production_schema import PRODUCTION_PLAN_SCHEMA
from .production_validation import validate_display_text, validate_render_asset
from .script_validation import script_content_digest
from .validation import ReportValidationError, validate_json_schema


VISUAL_SCENE_TYPES = {
    "timeline": "timeline_motion", "bar": "bar_motion",
    "comparison": "comparison_motion", "diagram": "diagram_motion",
}
MATERIAL_SCENE_TYPES = {
    "official_document": "document_reveal", "webpage": "document_reveal",
    "document_screenshot": "screenshot_pan", "webpage_screenshot": "screenshot_pan",
    "product_ui": "screenshot_pan", "photo": "image_pan_zoom",
    "archive": "image_pan_zoom",
}


def production_plan_digest(plan: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        {key: value for key, value in plan.items() if key != "plan_digest"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _editorial(text: str) -> dict:
    return {"text": text, "text_kind": "editorial", "claim_ids": [], "evidence_link_ids": []}


def _factual(text: str, claim_ids: list, evidence_ids: list) -> dict:
    return {
        "text": text, "text_kind": "factual", "claim_ids": list(claim_ids),
        "evidence_link_ids": list(evidence_ids),
    }


def _visual_heading(text: str, visual: Mapping[str, Any]) -> dict:
    if re.search(r"\d", text):
        return _factual(text, visual["claim_ids"], visual["evidence_link_ids"])
    return _editorial(text)


def _visual_text(visual: Mapping[str, Any], report: ResearchReport) -> list:
    entries = [_visual_heading(str(visual["title"]), visual)]
    prevalidated = set()
    if str(visual.get("subtitle", "")).strip():
        entries.append(_visual_heading(str(visual["subtitle"]), visual))
    visual_type = visual["visual_type"]
    if visual_type == "timeline":
        for event in visual["events"]:
            approved = next((item for item in report.timeline if (
                item["date"] == event["date"] and item["event"] == event["label"]
                and item["claim_ids"] == event["claim_ids"]
                and item["evidence_link_ids"] == event["evidence_link_ids"]
            )), None)
            if approved is None:
                raise ProductionValidationError("Timeline 屏幕文字不是已批准 Research Timeline 的精确条目")
            date_entry = _factual(event["date"], event["claim_ids"], event["evidence_link_ids"])
            label_entry = _factual(event["label"], event["claim_ids"], event["evidence_link_ids"])
            for entry in (date_entry, label_entry):
                validate_display_text(
                    entry, report,
                    additional_grounded_texts=(approved["date"], approved["event"]),
                )
                prevalidated.add(id(entry))
                entries.append(entry)
    elif visual_type == "bar":
        for point in visual["data_points"]:
            entries.append(_factual(
                f'{point["label"]}：{point["value_label"]}',
                point["claim_ids"], point["evidence_link_ids"],
            ))
    elif visual_type == "comparison":
        for item in visual["comparison_items"]:
            entries.append(_factual(
                f'{item["label"]}：{item["left_text"]} / {item["right_text"]}',
                item["claim_ids"], item["evidence_link_ids"],
            ))
    elif visual_type == "diagram":
        evidence_by_claim = {}
        for link in report.evidence_links:
            evidence_by_claim.setdefault(link["claim_id"], []).append(link["id"])
        for node in visual["nodes"]:
            evidence = []
            for claim_id in node["claim_ids"]:
                evidence.extend(evidence_by_claim.get(claim_id, []))
            entries.append(_factual(node["label"], node["claim_ids"], list(dict.fromkeys(evidence))))
        for edge in visual["edges"]:
            if str(edge["label"]).strip() and not re.search(r"\d", str(edge["label"])):
                entries.append(_editorial(str(edge["label"])))
    for entry in entries:
        if id(entry) not in prevalidated:
            validate_display_text(entry, report)
    return entries


def _select_renderer(mode: str, visuals: list, profile: Mapping[str, Any]) -> str:
    if mode not in {"auto", "remotion", "hyperframes"}:
        raise ProductionValidationError("renderer_mode 只支持 auto、remotion 或 hyperframes")
    if mode != "auto":
        return mode
    supported = set()
    for visual in visuals:
        hints = set(visual.get("render_target_hints", []))
        if "remotion_candidate" in hints:
            supported.add("remotion")
        if "hyperframes_candidate" in hints:
            supported.add("hyperframes")
    if len(supported) == 1:
        return next(iter(supported))
    return str(profile["default_renderer"])


def prepare_production_plan(
    package: MaterialPackage,
    script: Any,
    report: Any,
    profile: Mapping[str, Any],
    material_asset_root: Any,
    *,
    created_at: str,
    production_id: str,
    renderer_mode: str = "auto",
) -> Dict[str, Any]:
    if package.status not in {"reviewed", "reviewed_with_warnings"}:
        raise ProductionValidationError("Production Plan 只接受正式 reviewed Material Package")
    if package.research_update_required["required"]:
        raise ProductionValidationError("Research update 未解决，不能生成 Production Plan")
    report_obj = report if isinstance(report, ResearchReport) else ResearchReport.from_dict(report)
    beat_ids = {beat["beat_id"] for beat in script.beats}
    materials = {item["material_id"]: item for item in package.materials}
    visuals = {item["visual_id"]: item for item in package.generated_visuals}
    scenes = []
    gaps = []

    def add_gap(cue: Mapping[str, Any], reason: str, fallback: str) -> None:
        gaps.append({
            "gap_id": f"PG{len(gaps) + 1:03d}", "cue_id": cue["cue_id"],
            "beat_id": cue["beat_id"], "reason": reason,
            "recommended_fallback": fallback,
        })

    selected_visuals = []
    for cue in package.cue_sheet:
        if cue["beat_id"] not in beat_ids:
            raise ProductionValidationError("Material Cue 引用了不存在的 Script Beat")
        visual_candidates = [
            visual for visual in package.generated_visuals
            if visual["beat_id"] == cue["beat_id"] and visual["eligibility_status"] == "ready_to_use"
        ]
        material_candidates = [
            item for item in package.materials if cue["cue_id"] in item["cue_ids"]
        ]
        selected_visual = visual_candidates[0] if visual_candidates else None
        selected_material = None
        if selected_visual is not None:
            validate_render_asset(selected_visual, material_asset_root, generated_visual=True)
            selected_visuals.append(selected_visual)
            scene_type = VISUAL_SCENE_TYPES[selected_visual["visual_type"]]
            source_visual_ids = [selected_visual["visual_id"]]
            source_material_ids = []
            screen_text = _visual_text(selected_visual, report_obj)
            duration = float(selected_visual["suggested_duration_seconds"])
            renderer_intent = str(selected_visual["animation_intent"])
            layout_intent = f'{selected_visual["visual_type"]} 分步建立，保持来源署名可读'
        else:
            for item in material_candidates:
                if item["eligibility_status"] != "ready_to_use":
                    add_gap(
                        cue, f'{item["title"]} 只有 {item["eligibility_status"]} 资格，未进入渲染。',
                        "保留真人口播，或使用已批准 Research 生成原创说明图。",
                    )
                    continue
                if not str(item.get("local_path", "")).strip():
                    add_gap(
                        cue, f'{item["title"]} 尚无经过 SHA 验证的合法本地文件。',
                        "保留真人口播，取得安全本地截图后重新制作。",
                    )
                    continue
                validate_render_asset(item, material_asset_root)
                if item["asset_type"] in MATERIAL_SCENE_TYPES:
                    selected_material = item
                    break
            if selected_material is not None:
                scene_type = MATERIAL_SCENE_TYPES[selected_material["asset_type"]]
                source_material_ids = [selected_material["material_id"]]
                source_visual_ids = []
                screen_text = [_editorial(selected_material["caption"] or selected_material["title"])]
                duration = float(cue["suggested_duration_seconds"])
                renderer_intent = "轻量推近或平移，不裁掉改变原意的上下文"
                layout_intent = "安全素材占主体，标题和来源署名位于 safe area"
            else:
                scene_type = "aroll_placeholder"
                source_material_ids = []
                source_visual_ids = []
                screen_text = [_editorial(str(profile["scene_defaults"]["aroll_placeholder_label"])), _editorial("辅助画面待补")]
                duration = float(cue["suggested_duration_seconds"])
                renderer_intent = "中性真人口播占位，不生成假主播"
                layout_intent = "保留真人画面空间，只显示简短编辑提示"
        frames = max(1, round(duration * int(profile["canvas"]["fps"])))
        scenes.append({
            "scene_id": f"S{len(scenes) + 1:03d}", "cue_id": cue["cue_id"],
            "beat_id": cue["beat_id"], "placement_anchor": cue["placement_anchor"],
            "visual_role": cue["visual_role"], "source_material_ids": source_material_ids,
            "source_visual_ids": source_visual_ids, "scene_type": scene_type,
            "duration_seconds": frames / int(profile["canvas"]["fps"]),
            "duration_frames": frames, "renderer_intent": renderer_intent,
            "transition_intent": str(profile["scene_defaults"]["transition"]),
            "layout_intent": layout_intent, "on_screen_text": screen_text,
            "audio_mode": "aroll_placeholder" if scene_type == "aroll_placeholder" else "none",
            "warnings": [],
        })
    if not scenes:
        raise ProductionValidationError("Material Package 没有可建立 Production Scene 的 Cue")
    add_gap(
        package.cue_sheet[0], "当前时长来自建议值，尚无真实语音时间码。",
        "录制真人口播后再进行音频级精确对齐。",
    )
    expected_assets = [
        {
            "motion_asset_id": f"MA{index:03d}", "scene_id": scene["scene_id"],
            "asset_kind": "motion_clip", "requested_format": "mp4",
        }
        for index, scene in enumerate(scenes, 1)
    ]
    expected_assets.extend([
        {"motion_asset_id": "MAPREVIEW", "scene_id": scenes[0]["scene_id"],
         "asset_kind": "rough_preview", "requested_format": "mp4"},
        {"motion_asset_id": "HERO001", "scene_id": scenes[-1]["scene_id"],
         "asset_kind": "hero_still", "requested_format": "png"},
    ])
    selected_renderer = _select_renderer(renderer_mode, selected_visuals, profile)
    data = {
        "artifact_version": "0.6", "production_id": production_id, "revision": 1,
        "previous_revision": 0, "created_at": created_at, "generated_at": created_at,
        "script_id": script.script_id, "script_revision": script.revision,
        "script_content_digest": script_content_digest(script.data),
        "material_package_id": package.package_id,
        "material_package_revision": package.revision,
        "material_package_digest": package.package_digest,
        "material_review_id": package.review_state["review_id"],
        "production_profile_version": profile["profile_version"],
        "renderer_mode": renderer_mode, "selected_renderer": selected_renderer,
        "canvas": deepcopy(profile["canvas"]), "scenes": scenes,
        "motion_assets": expected_assets, "production_gaps": gaps,
        "warnings": list(package.warnings), "qa_state": {"state": "not_run"},
    }
    data["plan_digest"] = production_plan_digest(data)
    validate_production_plan(data, package, script, profile, report=report_obj)
    return data


def validate_production_plan(
    plan: Mapping[str, Any], package: MaterialPackage, script: Any,
    profile: Mapping[str, Any], *, report: Any = None,
) -> None:
    try:
        validate_json_schema(dict(plan), PRODUCTION_PLAN_SCHEMA, "production_plan")
    except ReportValidationError as exc:
        raise ProductionValidationError(str(exc)) from None
    if plan["plan_digest"] != production_plan_digest(plan):
        raise ProductionValidationError("Production Plan digest 无效")
    expected_binding = (
        script.script_id, script.revision, script_content_digest(script.data),
        package.package_id, package.revision, package.package_digest,
        package.review_state["review_id"], profile["profile_version"], profile["canvas"],
    )
    actual_binding = (
        plan["script_id"], plan["script_revision"], plan["script_content_digest"],
        plan["material_package_id"], plan["material_package_revision"],
        plan["material_package_digest"], plan["material_review_id"],
        plan["production_profile_version"], plan["canvas"],
    )
    if actual_binding != expected_binding:
        raise ProductionValidationError("Production Plan input binding 无效")
    cue_ids = {cue["cue_id"] for cue in package.cue_sheet}
    beat_ids = {beat["beat_id"] for beat in script.beats}
    material_ids = {item["material_id"] for item in package.materials}
    visual_by_id = {item["visual_id"]: item for item in package.generated_visuals}
    visual_ids = set(visual_by_id)
    expected_scene_ids = [f"S{index:03d}" for index in range(1, len(plan["scenes"]) + 1)]
    if [scene["scene_id"] for scene in plan["scenes"]] != expected_scene_ids:
        raise ProductionValidationError("Production Scene ID 必须由程序连续生成")
    for scene in plan["scenes"]:
        if scene["cue_id"] not in cue_ids:
            raise ProductionValidationError("Production Scene 引用了不存在的 Cue")
        if scene["beat_id"] not in beat_ids:
            raise ProductionValidationError("Production Scene 引用了不存在的 Beat")
        if not set(scene["source_material_ids"]) <= material_ids:
            raise ProductionValidationError("Production Scene 引用了不存在的 Material")
        if not set(scene["source_visual_ids"]) <= visual_ids:
            raise ProductionValidationError("Production Scene 引用了不存在的 Visual")
        if scene["duration_frames"] != round(scene["duration_seconds"] * plan["canvas"]["fps"]):
            raise ProductionValidationError("Production Scene duration 不确定或与 frame 数不一致")
        if report is not None:
            additional_grounding = []
            for visual_id in scene["source_visual_ids"]:
                visual = visual_by_id[visual_id]
                if visual["visual_type"] == "timeline":
                    for event in visual["events"]:
                        approved = next((item for item in report.timeline if (
                            item["date"] == event["date"] and item["event"] == event["label"]
                            and item["claim_ids"] == event["claim_ids"]
                            and item["evidence_link_ids"] == event["evidence_link_ids"]
                        )), None)
                        if approved is None:
                            raise ProductionValidationError("Production Plan Timeline 与 Research Timeline 不一致")
                        additional_grounding.extend((approved["date"], approved["event"]))
            for entry in scene["on_screen_text"]:
                validate_display_text(
                    entry, report,
                    additional_grounded_texts=tuple(additional_grounding),
                )
    for index, item in enumerate(plan["motion_assets"], 1):
        if item["asset_kind"] == "motion_clip" and item["motion_asset_id"] != f"MA{index:03d}":
            raise ProductionValidationError("Motion Asset ID 必须由程序生成")
        if item["scene_id"] not in set(expected_scene_ids):
            raise ProductionValidationError("Motion Asset 引用了不存在的 Scene")
