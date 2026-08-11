"""Canonical one-renderer Motion Production workflow for DeepTalk Studio 0.6."""

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from .material_profile import load_material_profile
from .production_planner import prepare_production_plan
from .production_profile import load_production_profile
from .production_qa import (
    Probe,
    build_motion_asset_manifest,
    prepare_production_qa,
    probe_media,
)
from .production_renderer import render_production_summary
from .production_renderers import get_renderer
from .production_renderers.base import PreparedProject, RenderBatch, RendererError
from .production_storage import save_production_artifact, save_production_plan
from .production_validation import validate_production_input


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCTION_PACKAGES = REPO_ROOT / "production_packages"
DEFAULT_PRODUCTION_ASSETS = REPO_ROOT / "production_assets"
DEFAULT_PRODUCTION_PROJECTS = REPO_ROOT / "production_projects"


@dataclass(frozen=True)
class ProductionWorkflowResult:
    plan: Dict[str, Any]
    manifest: Dict[str, Any]
    qa: Dict[str, Any]
    plan_path: Path
    manifest_path: Path
    qa_path: Path
    project_dir: Optional[Path]
    summary: str
    environment: Mapping[str, str]


def detect_production_environment() -> Dict[str, str]:
    """Return auditable local runtime versions without mutating the environment."""

    commands = {
        "node": ["node", "--version"],
        "npm": ["npm", "--version"],
        "npx": ["npx", "--version"],
        "ffmpeg": ["ffmpeg", "-version"],
        "ffprobe": ["ffprobe", "-version"],
    }
    result = {}
    for name, command in commands.items():
        if shutil.which(command[0]) is None:
            result[name] = "missing"
            continue
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=15, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            result[name] = "unavailable"
            continue
        first_line = (completed.stdout or completed.stderr).strip().splitlines()
        result[name] = first_line[0][:240] if completed.returncode == 0 and first_line else "unavailable"
    return result


def _generated_id(prefix: str, created_at: str) -> str:
    timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%S%f")
    return f"{prefix}-{timestamp}"


def run_production_workflow(
    package_path: Path,
    script: Any,
    report: Any,
    *,
    material_asset_root: Path,
    package_root: Path = DEFAULT_PRODUCTION_PACKAGES,
    asset_root: Path = DEFAULT_PRODUCTION_ASSETS,
    project_root: Path = DEFAULT_PRODUCTION_PROJECTS,
    renderer_mode: str = "auto",
    material_profile: Optional[Mapping[str, Any]] = None,
    production_profile: Optional[Mapping[str, Any]] = None,
    renderer_factory: Callable[[str], Any] = get_renderer,
    created_at: Optional[str] = None,
    production_id: Optional[str] = None,
    manifest_id: Optional[str] = None,
    qa_id: Optional[str] = None,
    probe_func: Probe = probe_media,
) -> ProductionWorkflowResult:
    """Validate V0.5.1 input, produce one plan, render, probe, gate and store."""

    timestamp = created_at or datetime.now().astimezone().isoformat()
    chosen_production_id = production_id or _generated_id("PROD", timestamp)
    chosen_manifest_id = manifest_id or _generated_id("MAM", timestamp)
    chosen_qa_id = qa_id or _generated_id("PQA", timestamp)
    material_config = dict(material_profile or load_material_profile())
    production_config = dict(production_profile or load_production_profile())
    package = validate_production_input(
        Path(package_path), script, report, material_config
    )
    plan = prepare_production_plan(
        package, script, report, production_config, Path(material_asset_root),
        created_at=timestamp, production_id=chosen_production_id,
        renderer_mode=renderer_mode,
    )
    plan_path = save_production_plan(plan, Path(package_root))

    # Ordinary production creates exactly one adapter: the renderer selected by the plan.
    renderer = renderer_factory(str(plan["selected_renderer"]))
    if renderer.name != plan["selected_renderer"]:
        raise RendererError("Renderer factory 返回了与 Production Plan 不一致的引擎")
    environment = detect_production_environment()
    required = ("node", "npm", "npx", "ffmpeg", "ffprobe")
    package_failures = []
    missing = [name for name in required if environment.get(name) in {"missing", "unavailable"}]
    if missing:
        package_failures.append({
            "issue_type": "production_environment_unavailable",
            "details": "制作环境缺少或无法使用：" + "、".join(missing),
        })

    checks = {"environment": not missing, "project_validation": False, "preview": False}
    prepared: Optional[PreparedProject] = None
    batch = RenderBatch((), ())
    if not missing:
        try:
            prepared = renderer.prepare_project(
                plan, package, production_config, Path(material_asset_root), Path(project_root)
            )
            renderer.validate_project(prepared)
            checks["project_validation"] = True
        except (OSError, RendererError, ValueError) as exc:
            package_failures.append({
                "issue_type": "renderer_validation_failed", "details": str(exc),
            })
        if checks["project_validation"] and prepared is not None:
            try:
                renderer.preview(prepared)
                checks["preview"] = True
            except (OSError, RendererError, ValueError) as exc:
                package_failures.append({
                    "issue_type": "renderer_preview_failed", "details": str(exc),
                })
            try:
                batch = renderer.render(prepared, plan, Path(asset_root))
            except (OSError, RendererError, ValueError) as exc:
                package_failures.append({
                    "issue_type": "renderer_batch_failed", "details": str(exc),
                })

    manifest_result = build_motion_asset_manifest(
        plan, str(plan["selected_renderer"]), batch,
        created_at=timestamp, manifest_id=chosen_manifest_id, probe_func=probe_func,
    )
    qa = prepare_production_qa(
        plan, manifest_result, created_at=timestamp, qa_id=chosen_qa_id,
        renderer_checks=checks, package_failures=package_failures,
    )
    manifest_path = save_production_artifact(
        manifest_result.manifest, plan_path, "motion-asset-manifest-r0001.json"
    )
    qa_path = save_production_artifact(
        qa, plan_path, "production-qa-r0001.json"
    )
    ready_count = len(manifest_result.manifest["assets"])
    failed_count = sum(1 for item in qa["clip_results"] if item["status"] == "failed")
    summary = render_production_summary(
        plan, ready_count=ready_count, failed_count=failed_count
    )
    return ProductionWorkflowResult(
        plan, manifest_result.manifest, qa, plan_path, manifest_path, qa_path,
        prepared.project_dir if prepared else None, summary, environment,
    )
