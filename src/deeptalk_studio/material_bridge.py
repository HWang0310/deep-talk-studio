"""Compatibility projection from canonical reviewed Material history to production."""

import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping

from .material_storage import MaterialStorageError, load_material_package
from .production_validation import ProductionValidationError, _inside, _validate_file_type
from .material_capture_manifest import (
    MaterialCaptureManifestError,
    MaterialCaptureManifestNotFound,
    load_material_capture_manifest,
)


class MaterialBridgeError(ValueError):
    """Reviewed Material cannot truthfully form a production view."""


def _digest(value: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(value)); payload.pop("view_digest", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _validate_local(item: Mapping[str, Any], asset_root: Path) -> str:
    raw = str(item.get("local_path", "")).strip()
    if not raw:
        return "missing_asset"
    path = Path(raw).resolve()
    root = Path(asset_root).resolve()
    if not _inside(path, root) or path.is_symlink() or not path.is_file():
        return "rejected"
    if path.stat().st_size <= 0 or path.stat().st_size != int(item.get("byte_size", -1)):
        return "rejected"
    if hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
        return "rejected"
    if item.get("asset_type") == "video_clip_reference":
        if path.suffix.casefold() not in {".mp4", ".mov", ".m4v"}:
            return "rejected"
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
                check=True, capture_output=True, text=True,
            )
            if not json.loads(probe.stdout).get("streams"):
                return "rejected"
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
            return "rejected"
    else:
        try:
            _validate_file_type(path)
        except ProductionValidationError:
            return "rejected"
    if path.suffix.casefold() == ".pdf":
        return "missing_asset"
    return "ready"


def _review_issues(path: Path, package) -> list:
    state = package.review_state
    review_path = path.parent / f"material-review-for-r{state['reviewed_from_revision']:04d}-{state['review_id']}.json"
    try:
        artifact = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MaterialBridgeError("Material Review Artifact 不可用") from exc
    return list(artifact.get("issues", []))


def build_material_production_view(
    package_path, script, report, profile, asset_root, *, artifact_resolver=None
) -> Dict[str, Any]:
    try:
        package = load_material_package(Path(package_path), script, report, profile)
    except MaterialStorageError as exc:
        raise MaterialBridgeError(f"Material canonical replay 失败：{exc}") from exc
    if package.status not in {"reviewed", "reviewed_with_warnings", "blocked"} or package.review_state["state"] != "reviewed":
        raise MaterialBridgeError("只能投影已完成独立 Review 的 Material Package")
    issues = _review_issues(Path(package_path), package)
    non_rights_blocks = {
        item_id
        for issue in issues
        if issue.get("severity") == "blocking" and issue.get("issue_type") not in {"rights_misrepresented", "permission_needed"}
        for item_id in issue.get("material_ids", [])
    }
    try:
        capture_manifest = load_material_capture_manifest(
            Path(asset_root), package, artifact_resolver=artifact_resolver
        )
    except MaterialCaptureManifestNotFound:
        capture_manifest = None
        captured_by_material_id = {}
    except MaterialCaptureManifestError as exc:
        raise MaterialBridgeError(f"Material Capture Manifest 验证失败：{exc}") from exc
    else:
        captured_by_material_id = {
            record["material_id"]: record for record in capture_manifest["records"]
        }
    items = []
    for item in package.materials:
        production_item = deepcopy(item)
        recorded_local_path = str(production_item.get("local_path", ""))
        capture_record = captured_by_material_id.get(item["material_id"])
        if capture_record is not None:
            recorded_local_path = capture_record["local_path"]
            if artifact_resolver is not None:
                try:
                    capture_path = artifact_resolver.resolve_material_capture(
                        package.package_id, capture_record
                    ).resolved_path
                except ValueError as exc:
                    raise MaterialBridgeError(
                        f"Material Capture runtime resolution 失败：{exc}"
                    ) from None
            else:
                capture_path = Path(capture_record["local_path"]).resolve()
            production_item.update(
                local_path=str(capture_path),
                byte_size=capture_record["byte_size"],
                sha256=capture_record["sha256"],
            )
        elif artifact_resolver is not None and recorded_local_path:
            try:
                production_item["local_path"] = str(
                    artifact_resolver.resolve_acquired_material(
                        package.package_id, production_item
                    ).resolved_path
                )
            except ValueError as exc:
                raise MaterialBridgeError(
                    f"Material Package runtime resolution 失败：{exc}"
                ) from None
        if item["material_id"] in non_rights_blocks or item["provenance_status"] != "inspected":
            status = "rejected"
        else:
            status = _validate_local(production_item, Path(asset_root))
        items.append({
            "source_kind": "material", "source_id": item["material_id"],
            "cue_ids": list(item["cue_ids"]), "title": item["title"], "caption": item["caption"],
            "asset_type": item["asset_type"], "capture": deepcopy(item["capture"]),
            "video_reference": deepcopy(item["video_reference"]),
            "source_url": item["source_url"], "normalized_source_url": item["normalized_source_url"],
            "provenance_status": item["provenance_status"],
            "historical_eligibility_status": item["eligibility_status"],
            "rights_status": item["rights_status"], "rights_basis": item["rights_basis"],
            "recorded_local_path": recorded_local_path,
            "local_path": production_item["local_path"], "byte_size": production_item["byte_size"], "sha256": production_item["sha256"],
            "production_status": status,
        })
    for visual in package.generated_visuals:
        production_visual = deepcopy(visual)
        recorded_local_path = str(visual.get("local_path", ""))
        if artifact_resolver is not None and visual["render_status"] == "rendered" and recorded_local_path:
            try:
                production_visual["local_path"] = str(
                    artifact_resolver.resolve_generated_visual(
                        package.package_id, visual
                    ).resolved_path
                )
            except ValueError as exc:
                raise MaterialBridgeError(
                    f"Generated Visual runtime resolution 失败：{exc}"
                ) from None
        status = _validate_local(production_visual, Path(asset_root)) if visual["render_status"] == "rendered" else "missing_asset"
        if visual["eligibility_status"] == "rejected": status = "rejected"
        items.append({
            "source_kind": "generated_visual", "source_id": visual["visual_id"],
            "cue_ids": [], "title": visual["title"], "caption": visual["title"],
            "asset_type": f"generated_{visual['visual_type']}", "capture": {},
            "video_reference": {"title": "", "start_seconds": 0, "end_seconds": 0, "usage_reason": ""},
            "source_url": "", "normalized_source_url": "", "provenance_status": "inspected",
            "historical_eligibility_status": visual["eligibility_status"],
            "rights_status": "not_applicable", "rights_basis": "DeepTalk Studio generated visual",
            "recorded_local_path": recorded_local_path,
            "local_path": production_visual["local_path"], "byte_size": visual["byte_size"], "sha256": visual["sha256"],
            "production_status": status,
        })
    view = {
        "artifact_version": "material-production-view/1",
        "package_id": package.package_id, "package_revision": package.revision,
        "package_digest": package.package_digest, "script_id": package.script_id,
        "script_revision": package.script_revision, "report_id": package.report_id,
        "report_revision": package.report_revision, "review_id": package.review_state["review_id"],
        "rights_reuse_affects_production_gate": False,
        "capture_manifest_digest": "" if capture_manifest is None else capture_manifest["manifest_digest"],
        "items": items,
    }
    view["view_digest"] = _digest(view)
    return view


def validate_material_production_view(
    view, package_path, script, report, profile, asset_root, *, artifact_resolver=None
) -> None:
    expected = build_material_production_view(
        package_path, script, report, profile, asset_root,
        artifact_resolver=artifact_resolver,
    )
    if dict(view) != expected or view.get("view_digest") != _digest(view):
        raise MaterialBridgeError("Material Production View 与 canonical replay 不一致")
