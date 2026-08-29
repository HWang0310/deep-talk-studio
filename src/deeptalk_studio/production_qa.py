"""File-backed Motion Asset Manifest and deterministic Production QA 0.6.1."""

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

from .production_profile import ProductionValidationError
from .production_renderers.base import RenderBatch, RendererCheckResult
from .production_schema import MOTION_ASSET_MANIFEST_SCHEMA, PRODUCTION_QA_SCHEMA
from .validation import ReportValidationError, validate_json_schema


Probe = Callable[[Path], Mapping[str, float]]


@dataclass(frozen=True)
class ManifestResult:
    manifest: Dict[str, Any]
    failures: Tuple[Mapping[str, str], ...]


def _digest(data: Mapping[str, Any], excluded: str) -> str:
    canonical = json.dumps(
        {key: value for key, value in data.items() if key != excluded},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def probe_media(path: Path) -> Mapping[str, float]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ProductionValidationError("Production QA 无法运行 ffprobe") from exc
    if completed.returncode != 0:
        raise ProductionValidationError("Production QA 无法读取 render 输出媒体信息")
    try:
        data = json.loads(completed.stdout)
        stream = data["streams"][0]
        rate = str(stream.get("r_frame_rate", "0/1"))
        numerator, denominator = rate.split("/", 1)
        fps = float(numerator) / float(denominator) if float(denominator) else 0.0
        duration = float(data.get("format", {}).get("duration", 0) or 0)
        return {
            "width": int(stream["width"]), "height": int(stream["height"]),
            "fps": fps, "duration_seconds": duration,
        }
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProductionValidationError("Production QA 的 ffprobe 输出无效") from exc


def _expected_duration(expected: Mapping[str, Any], plan: Mapping[str, Any]) -> float:
    if expected["asset_kind"] == "hero_still":
        return 0.0
    if expected["asset_kind"] == "rough_preview":
        return sum(float(scene["duration_seconds"]) for scene in plan["scenes"])
    scene = next(scene for scene in plan["scenes"] if scene["scene_id"] == expected["scene_id"])
    return float(scene["duration_seconds"])


def build_motion_asset_manifest(
    plan: Mapping[str, Any], renderer: str, batch: RenderBatch, *,
    created_at: str, manifest_id: str, probe_func: Probe = probe_media,
) -> ManifestResult:
    expected = {item["motion_asset_id"]: item for item in plan["motion_assets"]}
    scenes = {scene["scene_id"]: scene for scene in plan["scenes"]}
    failures = [dict(item) for item in batch.failures]
    assets = []
    output_ids = set()
    tolerance = 0.2
    for output in batch.outputs:
        output_ids.add(output.motion_asset_id)
        spec = expected.get(output.motion_asset_id)
        if spec is None or output.scene_id != spec["scene_id"] or output.asset_kind != spec["asset_kind"]:
            failures.append({
                "motion_asset_id": output.motion_asset_id,
                "issue_type": "production_plan_binding_mismatch",
                "details": "Renderer 输出与 Production Plan expected asset 不一致。",
            })
            continue
        path = Path(output.output_path).resolve()
        if not path.is_file():
            failures.append({"motion_asset_id": output.motion_asset_id, "issue_type": "missing_render_output", "details": "输出文件不存在。"})
            continue
        size = path.stat().st_size
        if size <= 0:
            failures.append({"motion_asset_id": output.motion_asset_id, "issue_type": "blank_render", "details": "输出文件为空。"})
            continue
        try:
            metadata = probe_func(path)
        except ProductionValidationError as exc:
            failures.append({"motion_asset_id": output.motion_asset_id, "issue_type": "invalid_render_output", "details": str(exc)})
            continue
        asset_failures = []
        if (int(metadata["width"]), int(metadata["height"])) != (
            int(plan["canvas"]["width"]), int(plan["canvas"]["height"]),
        ):
            asset_failures.append(("wrong_dimensions", "输出不是 Production Plan 要求的画布尺寸。"))
        if spec["asset_kind"] != "hero_still" and abs(float(metadata["fps"]) - float(plan["canvas"]["fps"])) > 0.05:
            asset_failures.append(("wrong_fps", "输出帧率与 Production Plan 不一致。"))
        expected_duration = _expected_duration(spec, plan)
        if spec["asset_kind"] != "hero_still" and abs(float(metadata["duration_seconds"]) - expected_duration) > tolerance:
            asset_failures.append(("invalid_duration", "输出时长超出允许误差。"))
        if asset_failures:
            failures.extend({"motion_asset_id": output.motion_asset_id, "issue_type": issue, "details": details} for issue, details in asset_failures)
            continue
        scene = scenes[output.scene_id]
        assets.append({
            "motion_asset_id": output.motion_asset_id, "scene_id": output.scene_id,
            "asset_kind": output.asset_kind, "renderer": renderer,
            "output_path": str(path), "format": path.suffix.casefold().lstrip("."),
            "width": int(metadata["width"]), "height": int(metadata["height"]),
            "fps": float(metadata["fps"]), "duration_seconds": float(metadata["duration_seconds"]),
            "byte_size": size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_material_ids": list(scene["source_material_ids"]),
            "source_visual_ids": list(scene["source_visual_ids"]),
            "production_plan_digest": plan["plan_digest"], "rendered_at": created_at,
            "render_command_summary": output.command_summary, "qa_status": "ready",
        })
    failure_ids = {item["motion_asset_id"] for item in failures}
    for asset_id in expected:
        if asset_id not in output_ids and asset_id not in failure_ids:
            failures.append({
                "motion_asset_id": asset_id, "issue_type": "missing_render_output",
                "details": "Renderer 没有返回该计划输出。",
            })
        elif asset_id not in output_ids and not any(
            item["motion_asset_id"] == asset_id and item["issue_type"] == "missing_render_output"
            for item in failures
        ):
            failures.append({
                "motion_asset_id": asset_id, "issue_type": "missing_render_output",
                "details": "Renderer 失败后没有可检查的真实输出文件。",
            })
    manifest = {
        "artifact_version": "0.6.1", "manifest_id": manifest_id,
        "production_id": plan["production_id"],
        "production_plan_digest": plan["plan_digest"], "renderer": renderer,
        "created_at": created_at, "assets": assets,
    }
    manifest["manifest_digest"] = _digest(manifest, "manifest_digest")
    validate_motion_manifest(manifest, plan)
    return ManifestResult(manifest, tuple(failures))


def validate_motion_manifest(
    manifest: Mapping[str, Any], plan: Mapping[str, Any], *, artifact_resolver=None
) -> Mapping[str, Any]:
    try:
        validate_json_schema(dict(manifest), MOTION_ASSET_MANIFEST_SCHEMA, "motion_asset_manifest")
    except ReportValidationError as exc:
        raise ProductionValidationError(str(exc)) from None
    if manifest["production_id"] != plan["production_id"] or manifest["production_plan_digest"] != plan["plan_digest"]:
        raise ProductionValidationError("Motion Asset Manifest 与 Production Plan binding 无效")
    if manifest["manifest_digest"] != _digest(manifest, "manifest_digest"):
        raise ProductionValidationError("Motion Asset Manifest digest 无效")
    expected = {item["motion_asset_id"]: item for item in plan["motion_assets"]}
    observations = {}
    for asset in manifest["assets"]:
        spec = expected.get(asset["motion_asset_id"])
        if spec is None or spec["scene_id"] != asset["scene_id"] or spec["asset_kind"] != asset["asset_kind"]:
            raise ProductionValidationError("Motion Asset 与 Production Plan expected output 不一致")
        if artifact_resolver is not None:
            try:
                observation = artifact_resolver.resolve_motion_asset(plan, asset)
            except ValueError as exc:
                raise ProductionValidationError(
                    f"Motion Asset runtime resolution 失败：{exc}"
                ) from None
            path = observation.resolved_path
            observations[asset["motion_asset_id"]] = observation
        else:
            path = Path(asset["output_path"])
            if not path.is_file() or path.stat().st_size != asset["byte_size"]:
                raise ProductionValidationError("Motion Asset 文件不存在或大小被修改")
            if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
                raise ProductionValidationError("Motion Asset SHA-256 被修改")
        if (asset["width"], asset["height"]) != (plan["canvas"]["width"], plan["canvas"]["height"]):
            raise ProductionValidationError("Motion Asset 尺寸无效")
    return observations


def prepare_production_qa(
    plan: Mapping[str, Any], manifest_result: ManifestResult, *, created_at: str,
    qa_id: str, renderer_checks: Sequence[Any],
) -> Dict[str, Any]:
    manifest = manifest_result.manifest
    validate_motion_manifest(manifest, plan)
    checks = [
        dict(item.to_dict() if isinstance(item, RendererCheckResult) else item)
        for item in renderer_checks
    ]
    issues = []
    for check in checks:
        if check["outcome"] != "fail":
            continue
        if check["command_category"] == "environment":
            issue_type = "production_environment_unavailable"
        elif check["command_category"] == "preview":
            issue_type = "renderer_preview_failed"
        else:
            issue_type = "renderer_validation_failed"
        issues.append({
            "issue_id": f"PQI{len(issues) + 1:03d}", "issue_type": issue_type,
            "scope": "package", "motion_asset_id": "", "blocking": True,
            "details": f'{check["check_name"]}: {check["summary"]}',
        })
    for failure in manifest_result.failures:
        issues.append({
            "issue_id": f"PQI{len(issues) + 1:03d}", "issue_type": failure["issue_type"],
            "scope": "clip", "motion_asset_id": failure["motion_asset_id"],
            "blocking": True, "details": failure["details"],
        })
    ready_ids = {asset["motion_asset_id"] for asset in manifest["assets"]}
    clip_results = [
        {"motion_asset_id": item["motion_asset_id"], "status": "ready" if item["motion_asset_id"] in ready_ids else "failed"}
        for item in plan["motion_assets"]
    ]
    package_block = any(issue["scope"] == "package" and issue["blocking"] for issue in issues)
    if package_block or not ready_ids:
        gate = "fail"
    elif any(result["status"] == "failed" for result in clip_results):
        gate = "warnings"
    else:
        gate = "pass"
    qa = {
        "artifact_version": "0.6.1", "qa_id": qa_id, "production_id": plan["production_id"],
        "production_plan_digest": plan["plan_digest"],
        "manifest_digest": manifest["manifest_digest"], "created_at": created_at,
        "checks": checks, "issues": issues, "clip_results": clip_results,
        "package_gate_status": gate,
    }
    qa["qa_digest"] = _digest(qa, "qa_digest")
    validate_production_qa(qa, plan, manifest)
    return qa


def validate_production_qa(
    qa: Mapping[str, Any], plan: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    try:
        validate_json_schema(dict(qa), PRODUCTION_QA_SCHEMA, "production_qa")
    except ReportValidationError as exc:
        raise ProductionValidationError(str(exc)) from None
    if (
        qa["production_id"] != plan["production_id"]
        or qa["production_plan_digest"] != plan["plan_digest"]
        or qa["manifest_digest"] != manifest["manifest_digest"]
    ):
        raise ProductionValidationError("Production QA binding 无效")
    if qa["qa_digest"] != _digest(qa, "qa_digest"):
        raise ProductionValidationError("Production QA digest 无效")
    expected_ids = [f"PQI{index:03d}" for index in range(1, len(qa["issues"]) + 1)]
    if [issue["issue_id"] for issue in qa["issues"]] != expected_ids:
        raise ProductionValidationError("Production QA issue ID 不是机器生成")
    issue_details = {
        issue["details"] for issue in qa["issues"]
        if issue["scope"] == "package" and issue["blocking"]
    }
    for check in qa["checks"]:
        expected_detail = f'{check["check_name"]}: {check["summary"]}'
        if check["outcome"] == "fail" and expected_detail not in issue_details:
            raise ProductionValidationError("Renderer fail check 必须确定性生成 blocking issue")
    ready_ids = {asset["motion_asset_id"] for asset in manifest["assets"]}
    expected_results = [
        {"motion_asset_id": item["motion_asset_id"], "status": "ready" if item["motion_asset_id"] in ready_ids else "failed"}
        for item in plan["motion_assets"]
    ]
    if qa["clip_results"] != expected_results:
        raise ProductionValidationError("Production QA clip result 被篡改")
    package_block = any(issue["scope"] == "package" and issue["blocking"] for issue in qa["issues"])
    if package_block or not ready_ids:
        expected_gate = "fail"
    elif any(item["status"] == "failed" for item in expected_results):
        expected_gate = "warnings"
    else:
        expected_gate = "pass"
    if qa["package_gate_status"] != expected_gate:
        raise ProductionValidationError("Production QA Gate 不能由模型自行声明")
