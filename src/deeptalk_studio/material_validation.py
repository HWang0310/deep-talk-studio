"""Fail-closed Material Package 0.5 derivation and cross-artifact checks."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Mapping, Optional

from .material_profile import MaterialValidationError
from .material_schema import (
    INSPECTION_MANIFEST_SCHEMA,
    MATERIAL_CONTENT_JSON_SCHEMA,
    MATERIAL_PACKAGE_JSON_SCHEMA,
    RIGHTS_MANIFEST_SCHEMA,
    SAFE_REUSE_STATUSES,
)
from .models import MaterialPackage, ResearchReport, ScriptDraft
from .script_profile import load_script_profile
from .script_validation import script_content_digest, validate_script_draft
from .sources import normalize_url
from .validation import ReportValidationError, validate_json_schema


def _schema(value: Any, schema: Dict[str, Any], path: str) -> None:
    try:
        validate_json_schema(value, schema, path)
    except ReportValidationError as exc:
        raise MaterialValidationError(str(exc)) from None


def _parse_time(value: str, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise MaterialValidationError(f"{field} 必须是 ISO 8601 日期时间") from None


def validate_material_inputs(
    script: Any,
    report: Any,
    material_profile: Mapping[str, Any],
    review_artifact: Optional[Mapping[str, Any]] = None,
) -> ScriptDraft:
    """Prove V0.4.1 review linkage and exact Research binding before searching."""

    script_data = script.to_dict() if hasattr(script, "to_dict") else deepcopy(script)
    if not isinstance(script_data, dict) or script_data.get("status") != "reviewed":
        raise MaterialValidationError("只有经过 V0.4.1 独立审查的 reviewed Script 才能准备素材")
    try:
        report_obj = report if isinstance(report, ResearchReport) else ResearchReport.from_dict(report)
        artifact = review_artifact
        if artifact is None and hasattr(script, "review_artifact"):
            artifact = script.review_artifact
        validated = ScriptDraft.from_dict(
            script_data, report_obj, load_script_profile(), artifact
        )
        validate_script_draft(validated, report_obj, load_script_profile(), artifact)
    except (ValueError, ReportValidationError) as exc:
        raise MaterialValidationError(f"Script Review 或 Research revision 验证失败：{exc}") from None
    if script_data["report_id"] != report_obj.report_id or script_data["report_revision"] != report_obj.revision:
        raise MaterialValidationError("Script 与 Research Report 的 revision 不一致")
    if material_profile.get("profile_version") != "0.5":
        raise MaterialValidationError("Material Workflow 必须使用 Profile 0.5")
    return validated


def _manifest_map(manifest: Mapping[str, Any], schema: Dict[str, Any], path: str) -> Dict[str, dict]:
    _schema(manifest, schema, path)
    result: Dict[str, dict] = {}
    for entry in manifest["entries"]:
        key = normalize_url(entry["url"])
        if key in result:
            raise MaterialValidationError(f"{path} 包含重复 URL")
        result[key] = deepcopy(entry)
    return result


def _validate_refs(ids: list, allowed: set, label: str) -> None:
    for value in ids:
        if value not in allowed:
            raise MaterialValidationError(f"{label} 引用了不存在的 ID：{value}")


def _validate_visual_specs(specs: list, script: ScriptDraft, report: ResearchReport) -> list:
    beat_ids = {beat["beat_id"] for beat in script.beats}
    claims = {claim["id"]: claim for claim in report.claims}
    links = {link["id"]: link for link in report.evidence_links}
    timeline_keys = {
        (item["date"], tuple(item["claim_ids"])) for item in report.timeline
    }
    result = []
    for index, raw in enumerate(specs, 1):
        spec = deepcopy(raw)
        if spec["beat_id"] not in beat_ids:
            raise MaterialValidationError("Visual Spec 引用了不存在的 Beat")
        _validate_refs(spec["claim_ids"], set(claims), "Visual Spec Claim")
        _validate_refs(spec["evidence_link_ids"], set(links), "Visual Spec Evidence")
        for link_id in spec["evidence_link_ids"]:
            if links[link_id]["claim_id"] not in spec["claim_ids"]:
                raise MaterialValidationError("Visual Spec Evidence 没有绑定其 Claim")
        if spec["visual_type"] == "timeline":
            if not spec["events"]:
                raise MaterialValidationError("timeline Visual 必须包含事件")
            for event in spec["events"]:
                if (event["date"], tuple(event["claim_ids"])) not in timeline_keys:
                    raise MaterialValidationError("timeline 事件必须来自已批准 Research timeline")
        if spec["visual_type"] == "bar":
            if not spec["data_points"]:
                raise MaterialValidationError("bar Visual 必须包含数据点")
            for point in spec["data_points"]:
                _validate_refs(point["claim_ids"], set(claims), "Visual data Claim")
                claim_text = " ".join(claims[cid]["claim"] for cid in point["claim_ids"])
                number = str(int(point["value"])) if float(point["value"]).is_integer() else str(point["value"])
                if number not in claim_text:
                    raise MaterialValidationError("generated_visual_unsupported_data：数值不在绑定 Claim 中")
        if spec["visual_type"] == "comparison" and not spec["comparison_items"]:
            raise MaterialValidationError("comparison Visual 必须包含比较项")
        if spec["visual_type"] == "diagram":
            node_ids = {node["node_id"] for node in spec["nodes"]}
            if not node_ids:
                raise MaterialValidationError("diagram Visual 必须包含节点")
            for edge in spec["edges"]:
                if edge["from_node"] not in node_ids or edge["to_node"] not in node_ids:
                    raise MaterialValidationError("diagram edge 引用了不存在的节点")
        spec.update(
            visual_id=f"V{index:03d}", width=1920, height=1080,
            render_status="not_rendered", local_path="", byte_size=0, sha256="",
            eligibility_status="ready_to_use",
        )
        result.append(spec)
    return result


def material_package_digest(data: Mapping[str, Any]) -> str:
    content = {key: data[key] for key in (
        "package_id", "revision", "script_id", "script_revision", "script_content_digest",
        "report_id", "report_revision", "cue_sheet", "materials", "generated_visuals",
        "gaps", "research_update_required", "warnings", "provider_provenance",
    )}
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def prepare_material_package(
    content: Dict[str, Any],
    script: Any,
    report: Any,
    material_profile: Mapping[str, Any],
    *,
    inspection_manifest: Optional[Mapping[str, Any]] = None,
    rights_manifest: Optional[Mapping[str, Any]] = None,
    created_at: str,
    package_id: str,
    package_mode: str = "codex_skill",
) -> MaterialPackage:
    report_obj = report if isinstance(report, ResearchReport) else ResearchReport.from_dict(report)
    validated_script = validate_material_inputs(
        script, report_obj, material_profile,
        getattr(script, "review_artifact", None),
    )
    _schema(content, MATERIAL_CONTENT_JSON_SCHEMA, "material_content")
    _parse_time(created_at, "created_at")
    if package_mode not in {"codex_skill", "openai_api", "fixture"}:
        raise MaterialValidationError("package_mode 无效")
    inspections = _manifest_map(
        inspection_manifest or {"entries": []}, INSPECTION_MANIFEST_SCHEMA, "inspection_manifest"
    )
    rights = _manifest_map(
        rights_manifest or {"entries": []}, RIGHTS_MANIFEST_SCHEMA, "rights_manifest"
    )
    beats = {beat["beat_id"]: beat for beat in validated_script.beats}
    cues = []
    cue_keys = set()
    for index, raw in enumerate(content["cue_sheet"], 1):
        if raw["beat_id"] not in beats:
            raise MaterialValidationError("Cue 引用了不存在的 Beat")
        anchor = raw["placement_anchor"].strip()
        if anchor not in beats[raw["beat_id"]]["narration"] or len(anchor) > 40:
            raise MaterialValidationError("Cue placement_anchor 必须是对应 Beat 中不超过 40 字的原句")
        key = (raw["beat_id"], anchor)
        if key in cue_keys:
            raise MaterialValidationError("Cue anchor 不能重复")
        cue_keys.add(key)
        cues.append({"cue_id": f"VC{index:03d}", **deepcopy(raw)})

    claims = {claim["id"]: claim for claim in report_obj.claims}
    links = {link["id"]: link for link in report_obj.evidence_links}
    seen_urls = set()
    materials = []
    for index, raw in enumerate(content["materials"], 1):
        item = deepcopy(raw)
        key = normalize_url(item["source_url"])
        if key in seen_urls:
            raise MaterialValidationError("素材 URL 规范化后重复，不能用镜像或追踪参数刷候选")
        seen_urls.add(key)
        cue_ids = []
        for number in item["cue_numbers"]:
            if number > len(cues):
                raise MaterialValidationError("素材引用了不存在的 Cue")
            cue_ids.append(cues[number - 1]["cue_id"])
        _validate_refs(item["claim_ids"], set(claims), "Material Claim")
        _validate_refs(item["evidence_link_ids"], set(links), "Material Evidence")
        if item["intended_role"] == "evidence":
            if not item["claim_ids"] or not item["evidence_link_ids"]:
                raise MaterialValidationError("Evidence 素材必须绑定 Claim 和 Evidence Link")
            for link_id in item["evidence_link_ids"]:
                if links[link_id]["claim_id"] not in item["claim_ids"]:
                    raise MaterialValidationError("Evidence 素材的 Evidence Link 与 Claim 不一致")
        if item["intended_role"] == "illustration" and not item["illustrative_only"]:
            raise MaterialValidationError("Illustration 必须明确 illustrative_only，不能冒充证据")
        inspection = inspections.get(key)
        rights_entry = rights.get(key)
        provenance_status = "inspected" if inspection else "unmatched"
        rights_status = rights_entry["rights_status"] if rights_entry else "unknown"
        if rights_entry and rights_status in {
            "explicit_reuse_allowed", "creative_commons", "official_press_asset"
        } and not rights_entry["license_url"].strip():
            raise MaterialValidationError("明确复用或 CC / press asset 必须保留 license URL")
        video = item["video_reference"]
        if item["asset_type"] == "video_clip_reference":
            if not video["title"].strip() or not video["usage_reason"].strip() or video["end_seconds"] <= video["start_seconds"]:
                raise MaterialValidationError("视频引用必须保留标题、有效起止秒数和使用理由")
        if rights_status in SAFE_REUSE_STATUSES and provenance_status == "inspected":
            eligibility = "ready_to_use"
        elif rights_status == "permission_required":
            eligibility = "permission_required"
        elif rights_status == "avoid":
            eligibility = "rejected"
        else:
            eligibility = "reference_only"
        scores = [item[field] for field in (
            "relevance", "grounding_strength", "visual_clarity", "reuse_safety", "acquisition_effort"
        )]
        if any(not 1 <= score <= 5 for score in scores):
            raise MaterialValidationError("Material ranking 五项评分必须在 1 到 5 之间")
        ranking = round(
            item["relevance"] * .30 + item["grounding_strength"] * .25
            + item["visual_clarity"] * .15 + item["reuse_safety"] * .20
            + (6 - item["acquisition_effort"]) * .10, 2
        )
        item.update(
            material_id=f"M{index:03d}", normalized_source_url=key, cue_ids=cue_ids,
            provenance_status=provenance_status,
            inspection_method=inspection["inspection_method"] if inspection else "not_inspected",
            inspected_at=inspection["inspected_at"] if inspection else "",
            inspection_reference=inspection["tool_reference"] if inspection else "",
            rights_status=rights_status,
            rights_basis=rights_entry["rights_basis"] if rights_entry else "未找到可核验的复用依据。",
            license_url=rights_entry["license_url"] if rights_entry else "",
            rights_verified_at=rights_entry["verified_at"] if rights_entry else "",
            rights_reference=rights_entry["tool_reference"] if rights_entry else "",
            eligibility_status=eligibility, ranking_score=ranking,
            local_path="", byte_size=0, sha256="",
            search_references=[],
        )
        materials.append(item)
    materials.sort(key=lambda item: (-item["ranking_score"], item["material_id"]))

    update_signals = deepcopy(content["research_update_signals"])
    for signal in update_signals:
        _validate_refs(signal["beat_ids"], set(beats), "Research update Beat")
        _validate_refs(signal["claim_ids"], set(claims), "Research update Claim")
    status = "research_update_required" if update_signals else "draft"
    data = {
        "artifact_version": "0.5", "package_id": package_id, "revision": 1,
        "previous_revision": 0, "created_at": created_at, "generated_at": created_at,
        "package_mode": package_mode, "status": status,
        "script_id": validated_script.script_id, "script_revision": validated_script.revision,
        "script_content_digest": script_content_digest(validated_script.data),
        "script_review_id": validated_script.review_state["review_id"],
        "report_id": report_obj.report_id, "report_revision": report_obj.revision,
        "material_profile_version": material_profile["profile_version"],
        "cue_sheet": cues, "materials": materials,
        "generated_visuals": _validate_visual_specs(
            content["visual_specs"], validated_script, report_obj
        ),
        "gaps": deepcopy(content["gaps"]),
        "research_update_required": {"required": bool(update_signals), "signals": update_signals},
        "warnings": deepcopy(content["warnings"]),
        "review_state": {
            "state": "not_reviewed", "review_id": "", "reviewed_from_revision": 0,
            "review_gate_status": "not_run", "reviewed_package_digest": "",
        },
        "provider_provenance": {
            "search_call_ids": [], "search_queries": [], "source_urls": [], "citation_urls": [],
        },
    }
    data["package_digest"] = material_package_digest(data)
    _schema(data, MATERIAL_PACKAGE_JSON_SCHEMA, "material_package")
    return MaterialPackage(data)


def apply_provider_search_provenance(package: MaterialPackage, provenance: Any) -> MaterialPackage:
    """Preserve API search evidence without pretending a search result was inspected."""

    data = package.to_dict()
    source_refs = {}
    call_ids, queries, source_urls = [], [], []
    for call in provenance.search_calls:
        call_ids.append(call.call_id)
        queries.extend(call.queries)
        source_urls.extend(call.source_urls)
        for url in call.source_urls:
            try:
                source_refs.setdefault(normalize_url(url), []).append(f"web_search_call:{call.call_id}")
            except ValueError:
                continue
    citation_urls = [citation.url for citation in provenance.citations]
    for citation in provenance.citations:
        try:
            source_refs.setdefault(normalize_url(citation.url), []).append(
                f"url_citation:{citation.output_item_id}:{citation.start_index}-{citation.end_index}"
            )
        except ValueError:
            continue
    for item in data["materials"]:
        refs = source_refs.get(item["normalized_source_url"], [])
        item["search_references"] = list(dict.fromkeys(refs))
        if refs and item["provenance_status"] == "unmatched":
            item["provenance_status"] = "discovered"
            item["eligibility_status"] = "reference_only"
    data["provider_provenance"] = {
        "search_call_ids": list(dict.fromkeys(call_ids)),
        "search_queries": list(dict.fromkeys(queries)),
        "source_urls": list(dict.fromkeys(source_urls)),
        "citation_urls": list(dict.fromkeys(citation_urls)),
    }
    data["package_digest"] = material_package_digest(data)
    _schema(data, MATERIAL_PACKAGE_JSON_SCHEMA, "material_package")
    return MaterialPackage(data)


def update_package_assets(
    package: MaterialPackage,
    *,
    material_records: Optional[Mapping[str, Mapping[str, Any]]] = None,
    visual_records: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> MaterialPackage:
    """Attach code-generated acquisition records without changing revision."""

    data = package.to_dict()
    material_map = material_records or {}
    visual_map = visual_records or {}
    known_materials = {item["material_id"] for item in data["materials"]}
    known_visuals = {item["visual_id"] for item in data["generated_visuals"]}
    if set(material_map) - known_materials or set(visual_map) - known_visuals:
        raise MaterialValidationError("Asset record 引用了不存在的素材或 Visual")
    for item in data["materials"]:
        record = material_map.get(item["material_id"])
        if record:
            if item["eligibility_status"] != "ready_to_use":
                raise MaterialValidationError("非 ready_to_use 素材不能附加本地文件")
            item.update(
                local_path=str(record["local_path"]), byte_size=int(record["byte_size"]),
                sha256=str(record["sha256"]),
            )
    for visual in data["generated_visuals"]:
        record = visual_map.get(visual["visual_id"])
        if record:
            visual.update(
                render_status="rendered", local_path=str(record["local_path"]),
                byte_size=int(record["byte_size"]), sha256=str(record["sha256"]),
            )
    data["package_digest"] = material_package_digest(data)
    return MaterialPackage(data)


def validate_material_package_integrity(
    package: Any,
    script: Any,
    report: Any,
    material_profile: Mapping[str, Any],
) -> MaterialPackage:
    data = package.to_dict() if hasattr(package, "to_dict") else deepcopy(package)
    _schema(data, MATERIAL_PACKAGE_JSON_SCHEMA, "material_package")
    validated_script = validate_material_inputs(
        script, report, material_profile, getattr(script, "review_artifact", None)
    )
    report_obj = report if isinstance(report, ResearchReport) else ResearchReport.from_dict(report)
    if data.get("artifact_version") != "0.5":
        raise MaterialValidationError("Material Package 版本无效")
    expected_binding = (
        validated_script.script_id, validated_script.revision,
        script_content_digest(validated_script.data), report_obj.report_id, report_obj.revision,
    )
    actual_binding = (
        data.get("script_id"), data.get("script_revision"), data.get("script_content_digest"),
        data.get("report_id"), data.get("report_revision"),
    )
    if actual_binding != expected_binding:
        raise MaterialValidationError("Material Package 的 Script / Research binding 不一致")
    if data.get("material_profile_version") != material_profile.get("profile_version"):
        raise MaterialValidationError("Material Package 的 Profile 版本不一致")
    if data.get("package_digest") != material_package_digest(data):
        raise MaterialValidationError("Material Package digest 与内容不一致")
    cue_ids = [cue.get("cue_id") for cue in data.get("cue_sheet", [])]
    material_ids = [item.get("material_id") for item in data.get("materials", [])]
    visual_ids = [item.get("visual_id") for item in data.get("generated_visuals", [])]
    if cue_ids != [f"VC{i:03d}" for i in range(1, len(cue_ids) + 1)]:
        raise MaterialValidationError("Cue ID 必须由程序连续生成")
    if len(material_ids) != len(set(material_ids)) or len(visual_ids) != len(set(visual_ids)):
        raise MaterialValidationError("Material / Visual ID 不能重复")
    if data.get("status") not in {
        "draft", "reviewed", "reviewed_with_warnings", "research_update_required", "blocked"
    }:
        raise MaterialValidationError("Material Package status 无效")
    review_state = data["review_state"]
    reviewed_statuses = {"reviewed", "reviewed_with_warnings", "blocked"}
    if data["status"] in reviewed_statuses and review_state["state"] != "reviewed":
        raise MaterialValidationError("已审 Material Package 缺少 Review linkage")
    if data["status"] == "draft" and review_state["state"] != "not_reviewed":
        raise MaterialValidationError("draft Material Package 不能携带 Review linkage")
    if data["status"] == "research_update_required" and review_state["state"] not in {"not_reviewed", "reviewed"}:
        raise MaterialValidationError("research_update_required Review linkage 无效")
    return MaterialPackage(data)
