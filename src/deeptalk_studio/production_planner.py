"""Deterministic Material Package → Production Plan 0.6.1 derivation."""

import hashlib
import json
import unicodedata
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

DISPLAY_CAPACITY_UNITS = {
    "comparison label": 32,
    "comparison fact": 72,
    "Diagram node": 52,
    "Diagram edge": 40,
}


def production_plan_digest(plan: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        {key: value for key, value in plan.items() if key != "plan_digest"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _editorial(text: str) -> dict:
    return {
        "text": text, "origin": "machine_editorial", "text_kind": "editorial",
        "claim_ids": [], "evidence_link_ids": [],
    }


def _factual(
    text: str, claim_ids: list, evidence_ids: list, *, origin: str = "visual_label",
    attribution: bool = False,
) -> dict:
    return {
        "text": text, "origin": origin,
        "text_kind": "attribution" if attribution else "factual",
        "claim_ids": list(claim_ids),
        "evidence_link_ids": list(evidence_ids),
    }


def _empty_payload(payload_type: str) -> dict:
    return {
        "payload_version": "0.6.1", "payload_type": payload_type,
        "timeline_events": [], "bar_data_points": [], "comparison_items": [],
        "diagram_nodes": [], "diagram_edges": [], "image_asset_id": "",
        "capture_region": "",
    }


def _display_units(text: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
        for character in str(text)
    )


def _require_display_capacity(text: str, field: str) -> None:
    if _display_units(text) > DISPLAY_CAPACITY_UNITS[field]:
        raise ProductionValidationError(
            f"{field} 文字超过确定性安全布局容量，不能进入 Renderer"
        )


def _visual_payload(visual: Mapping[str, Any], report: ResearchReport) -> tuple:
    visual_type = visual["visual_type"]
    headings = {
        "timeline": "关键时间点", "bar": "数据对比",
        "comparison": "要点对照", "diagram": "关系说明",
    }
    payload = _empty_payload(visual_type)
    if visual_type == "timeline":
        for index, event in enumerate(visual["events"], 1):
            approved = next((item for item in report.timeline if (
                item["date"] == event["date"] and item["event"] == event["label"]
                and item["claim_ids"] == event["claim_ids"]
                and item["evidence_link_ids"] == event["evidence_link_ids"]
            )), None)
            if approved is None:
                raise ProductionValidationError("Timeline 屏幕文字不是已批准 Research Timeline 的精确条目")
            date_entry = _factual(
                event["date"], event["claim_ids"], event["evidence_link_ids"],
                origin="research_fact",
            )
            label_entry = _factual(
                event["label"], event["claim_ids"], event["evidence_link_ids"],
                origin="research_fact",
            )
            for entry in (date_entry, label_entry):
                validate_display_text(
                    entry, report,
                    additional_grounded_texts=(approved["date"], approved["event"]),
                )
            payload["timeline_events"].append({
                "order": index, "date": date_entry, "label": label_entry,
            })
    elif visual_type == "bar":
        for index, point in enumerate(visual["data_points"], 1):
            label = _factual(point["label"], point["claim_ids"], point["evidence_link_ids"])
            value_label = _factual(point["value_label"], point["claim_ids"], point["evidence_link_ids"])
            validate_display_text(label, report)
            validate_display_text(value_label, report)
            payload["bar_data_points"].append({
                "order": index, "label": label, "value": point["value"],
                "value_label": value_label,
            })
    elif visual_type == "comparison":
        if len(visual["comparison_items"]) < 2:
            raise ProductionValidationError("Comparison Motion 至少需要 2 个已绑定条目")
        if len(visual["comparison_items"]) > 6:
            raise ProductionValidationError("Comparison Motion 最多支持 6 个安全可读卡片")
        for index, item in enumerate(visual["comparison_items"], 1):
            _require_display_capacity(item["label"], "comparison label")
            _require_display_capacity(item["left_text"], "comparison fact")
            _require_display_capacity(item["right_text"], "comparison fact")
            fields = {
                key: _factual(item[key], item["claim_ids"], item["evidence_link_ids"])
                for key in ("label", "left_text", "right_text")
            }
            for entry in fields.values():
                validate_display_text(entry, report)
            payload["comparison_items"].append({"order": index, **fields})
    elif visual_type == "diagram":
        if len(visual["nodes"]) > 6:
            raise ProductionValidationError("Diagram Motion 最多支持 6 个安全可读节点")
        evidence_by_claim = {}
        for link in report.evidence_links:
            evidence_by_claim.setdefault(link["claim_id"], []).append(link["id"])
        nodes_by_id = {node["node_id"]: node for node in visual["nodes"]}
        for index, node in enumerate(visual["nodes"], 1):
            _require_display_capacity(node["label"], "Diagram node")
            evidence = []
            for claim_id in node["claim_ids"]:
                evidence.extend(evidence_by_claim.get(claim_id, []))
            label = _factual(node["label"], node["claim_ids"], list(dict.fromkeys(evidence)))
            validate_display_text(label, report)
            payload["diagram_nodes"].append({
                "order": index, "node_id": node["node_id"], "label": label,
            })
        for index, edge in enumerate(visual["edges"], 1):
            _require_display_capacity(edge["label"], "Diagram edge")
            endpoint_claims = list(dict.fromkeys(
                nodes_by_id[edge["from_node"]]["claim_ids"]
                + nodes_by_id[edge["to_node"]]["claim_ids"]
            ))
            evidence = []
            for claim_id in endpoint_claims:
                evidence.extend(evidence_by_claim.get(claim_id, []))
            label = _factual(edge["label"], endpoint_claims, list(dict.fromkeys(evidence)))
            validate_display_text(label, report)
            payload["diagram_edges"].append({
                "order": index, "from_node": edge["from_node"],
                "to_node": edge["to_node"], "label": label,
            })
    return [_editorial(headings[visual_type])], payload


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
    episode_visual_preference: Mapping[str, Any] = None,
    post_alignment_visual_plan: Mapping[str, Any] = None,
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
            screen_text, scene_payload = _visual_payload(selected_visual, report_obj)
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
                if str(item["local_path"]).casefold().endswith(".pdf"):
                    add_gap(
                        cue, "文件已取得，但尚无可安全展示的页面截图。",
                        "在 V0.5 Material Workflow 登记带页码和区域信息的 PNG/JPEG/WebP 截图。",
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
                caption = _factual(
                    selected_material["caption"] or selected_material["title"],
                    selected_material["claim_ids"], selected_material["evidence_link_ids"],
                    origin="material_caption",
                )
                try:
                    validate_display_text(caption, report_obj)
                    screen_text = [caption]
                except ProductionValidationError:
                    screen_text = [_editorial("资料画面")]
                    add_gap(
                        cue, "素材说明文字无法从绑定 Claim 确定性回查，已使用中性标签。",
                        "人工核对说明文字后，在 Material Review 中重新登记。",
                    )
                scene_payload = _empty_payload("image")
                scene_payload["image_asset_id"] = selected_material["material_id"]
                scene_payload["capture_region"] = str(
                    selected_material.get("capture", {}).get("capture_region", "")
                )
                duration = float(cue["suggested_duration_seconds"])
                renderer_intent = "轻量推近或平移，不裁掉改变原意的上下文"
                layout_intent = "安全素材占主体，标题和来源署名位于 safe area"
            else:
                scene_type = "aroll_placeholder"
                source_material_ids = []
                source_visual_ids = []
                screen_text = [_editorial(str(profile["scene_defaults"]["aroll_placeholder_label"])), _editorial("辅助画面待补")]
                scene_payload = _empty_payload("aroll")
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
            "layout_intent": layout_intent, "scene_payload": scene_payload,
            "on_screen_text": screen_text,
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
        "artifact_version": "0.6.1", "production_id": production_id, "revision": 1,
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
    if (episode_visual_preference is None) != (post_alignment_visual_plan is None):
        raise ProductionValidationError("Episode Visual Preference 与 Post-Alignment Visual Plan 必须成对绑定")
    if episode_visual_preference is not None:
        preference_digest = str(episode_visual_preference.get("preference_digest", ""))
        visual_plan_digest = str(post_alignment_visual_plan.get("plan_digest", ""))
        if len(preference_digest) != 64 or len(visual_plan_digest) != 64:
            raise ProductionValidationError("Visual Context digest 无效")
        data.update(
            episode_visual_preference_digest=preference_digest,
            post_alignment_visual_plan_digest=visual_plan_digest,
        )
    data["plan_digest"] = production_plan_digest(data)
    validate_production_plan(data, package, script, profile, report=report_obj)
    return data


def validate_production_plan(
    plan: Mapping[str, Any], package: MaterialPackage, script: Any,
    profile: Mapping[str, Any], *, report: Any = None,
    episode_visual_preference: Mapping[str, Any] = None,
    post_alignment_visual_plan: Mapping[str, Any] = None,
) -> None:
    try:
        validate_json_schema(dict(plan), PRODUCTION_PLAN_SCHEMA, "production_plan")
    except ReportValidationError as exc:
        raise ProductionValidationError(str(exc)) from None
    if plan["plan_digest"] != production_plan_digest(plan):
        raise ProductionValidationError("Production Plan digest 无效")
    has_preference = "episode_visual_preference_digest" in plan
    has_visual_plan = "post_alignment_visual_plan_digest" in plan
    if has_preference != has_visual_plan:
        raise ProductionValidationError("Production Plan Visual Context binding 不完整")
    if (episode_visual_preference is None) != (post_alignment_visual_plan is None):
        raise ProductionValidationError("Visual Context validator 输入不完整")
    if episode_visual_preference is not None:
        if not has_preference or plan["episode_visual_preference_digest"] != episode_visual_preference.get("preference_digest") or plan["post_alignment_visual_plan_digest"] != post_alignment_visual_plan.get("plan_digest"):
            raise ProductionValidationError("Production Plan Visual Context binding 无效")
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
    expected_payload_types = {
        "timeline_motion": "timeline", "bar_motion": "bar",
        "comparison_motion": "comparison", "diagram_motion": "diagram",
        "document_reveal": "image", "screenshot_pan": "image",
        "image_pan_zoom": "image", "text_explainer": "aroll",
        "transition_card": "aroll", "aroll_placeholder": "aroll",
    }
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
        payload = scene["scene_payload"]
        if payload["payload_type"] != expected_payload_types[scene["scene_type"]]:
            raise ProductionValidationError("Production Scene payload 类型与 scene_type 不一致")
        groups = (
            payload["timeline_events"], payload["bar_data_points"],
            payload["comparison_items"], payload["diagram_nodes"],
            payload["diagram_edges"],
        )
        for group in groups:
            if [item["order"] for item in group] != list(range(1, len(group) + 1)):
                raise ProductionValidationError("Scene payload 元素顺序必须由程序连续生成")
        group_by_type = {
            "timeline": "timeline_events", "bar": "bar_data_points",
            "comparison": "comparison_items", "diagram": "diagram_nodes",
        }
        payload_group_keys = {
            "timeline_events", "bar_data_points", "comparison_items",
            "diagram_nodes", "diagram_edges",
        }
        allowed_groups = {group_by_type[payload["payload_type"]]} if payload["payload_type"] in group_by_type else set()
        if payload["payload_type"] == "diagram":
            allowed_groups.add("diagram_edges")
        if any(payload[key] for key in payload_group_keys - allowed_groups):
            raise ProductionValidationError("Scene payload 包含与类型无关的元素组")
        if payload["payload_type"] == "image":
            if payload["image_asset_id"] not in scene["source_material_ids"]:
                raise ProductionValidationError("Image scene payload 与 source material 不一致")
        elif payload["image_asset_id"] or payload["capture_region"]:
            raise ProductionValidationError("非图片 scene payload 不能携带图片字段")
        node_order = {item["node_id"]: item["order"] for item in payload["diagram_nodes"]}
        for edge in payload["diagram_edges"]:
            if edge["from_node"] not in node_order or edge["to_node"] not in node_order:
                raise ProductionValidationError("Diagram edge 端点不存在")
        if report is not None:
            additional_grounding = []
            for visual_id in scene["source_visual_ids"]:
                visual = visual_by_id[visual_id]
                expected_text, expected_payload = _visual_payload(visual, report)
                if scene["scene_payload"] != expected_payload or scene["on_screen_text"] != expected_text:
                    raise ProductionValidationError("Production Plan scene payload 与源 Visual 重新推导结果不一致")
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
            payload_entries = []
            for event in payload["timeline_events"]:
                payload_entries.extend((event["date"], event["label"]))
            for point in payload["bar_data_points"]:
                payload_entries.extend((point["label"], point["value_label"]))
            for item in payload["comparison_items"]:
                payload_entries.extend((item["label"], item["left_text"], item["right_text"]))
            for node in payload["diagram_nodes"]:
                payload_entries.append(node["label"])
            for edge in payload["diagram_edges"]:
                payload_entries.append(edge["label"])
            for entry in payload_entries:
                validate_display_text(
                    entry, report,
                    additional_grounded_texts=tuple(additional_grounding),
                )
    for index, item in enumerate(plan["motion_assets"], 1):
        if item["asset_kind"] == "motion_clip" and item["motion_asset_id"] != f"MA{index:03d}":
            raise ProductionValidationError("Motion Asset ID 必须由程序生成")
        if item["scene_id"] not in set(expected_scene_ids):
            raise ProductionValidationError("Motion Asset 引用了不存在的 Scene")
