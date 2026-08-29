"""Canonical one-renderer Motion Production workflow for DeepTalk Studio 0.6."""

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from .material_profile import load_material_profile
from .production_planner import prepare_production_plan
from .production_profile import ProductionValidationError, load_production_profile
from .production_qa import (
    Probe,
    build_motion_asset_manifest,
    prepare_production_qa,
    probe_media,
)
from .production_renderer import render_production_summary
from .production_renderers import get_renderer
from .production_renderers.base import (
    CommandResult, PreparedProject, RenderBatch, RendererCheckResult, RendererError,
)
from .production_storage import save_production_artifact, save_production_plan
from .production_validation import validate_production_input
from .artifact_runtime import (
    ArtifactRuntimeError, RuntimeArtifactResolver, load_artifact_runtime_config,
)


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


def _configured_artifact_resolver(material_asset_root: Path):
    """Load repo-local runtime truth only for the canonical material layout."""
    material_root = Path(material_asset_root).resolve()
    if material_root.name == "material_assets":
        repository_root = material_root.parent
    elif material_root.parent.name == "material_assets":
        repository_root = material_root.parent.parent
    else:
        return None
    try:
        return RuntimeArtifactResolver(load_artifact_runtime_config(repository_root))
    except ArtifactRuntimeError as exc:
        raise ProductionValidationError(
            f"Artifact runtime configuration 无效：{exc}"
        ) from None


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
    episode_visual_preference: Optional[Mapping[str, Any]] = None,
    post_alignment_visual_plan: Optional[Mapping[str, Any]] = None,
    artifact_resolver=None,
) -> ProductionWorkflowResult:
    """Validate V0.5.1 input, produce one plan, render, probe, gate and store."""

    timestamp = created_at or datetime.now().astimezone().isoformat()
    chosen_production_id = production_id or _generated_id("PROD", timestamp)
    chosen_manifest_id = manifest_id or _generated_id("MAM", timestamp)
    chosen_qa_id = qa_id or _generated_id("PQA", timestamp)
    material_config = dict(material_profile or load_material_profile())
    production_config = dict(production_profile or load_production_profile())
    if artifact_resolver is None:
        artifact_resolver = _configured_artifact_resolver(Path(material_asset_root))
    package = validate_production_input(
        Path(package_path), script, report, material_config
    )
    plan = prepare_production_plan(
        package, script, report, production_config, Path(material_asset_root),
        created_at=timestamp, production_id=chosen_production_id,
        renderer_mode=renderer_mode,
        episode_visual_preference=episode_visual_preference,
        post_alignment_visual_plan=post_alignment_visual_plan,
        artifact_resolver=artifact_resolver,
    )
    plan_path = save_production_plan(plan, Path(package_root))

    # Ordinary production creates exactly one adapter: the renderer selected by the plan.
    renderer = renderer_factory(str(plan["selected_renderer"]))
    if renderer.name != plan["selected_renderer"]:
        raise RendererError("Renderer factory 返回了与 Production Plan 不一致的引擎")
    environment = detect_production_environment()
    required = ("node", "npm", "npx", "ffmpeg", "ffprobe")
    missing = [name for name in required if environment.get(name) in {"missing", "unavailable"}]
    checks = [RendererCheckResult(
        "environment", "core", 0 if not missing else -1,
        "pass" if not missing else "fail", "environment",
        "制作环境可用。" if not missing else "制作环境缺少或无法使用：" + "、".join(missing),
    )]
    prepared: Optional[PreparedProject] = None
    batch = RenderBatch((), ())
    if not missing:
        try:
            prepared = renderer.prepare_project(
                plan, package, production_config, Path(material_asset_root), Path(project_root),
                artifact_resolver=artifact_resolver,
            )
            validation_checks = list(renderer.validate_project(prepared))
            for item in validation_checks:
                if isinstance(item, RendererCheckResult):
                    checks.append(item)
                elif isinstance(item, CommandResult):
                    checks.append(RendererCheckResult(
                        "renderer_validation", renderer.name, item.exit_code,
                        "pass" if item.exit_code == 0 else "fail", "validate",
                        item.stderr_summary or item.stdout_summary or "项目验证完成。",
                    ))
        except (OSError, RendererError, ValueError) as exc:
            checks.append(RendererCheckResult(
                "renderer_validation", renderer.name, -1, "fail", "validate", str(exc),
            ))
        validation_passed = prepared is not None and all(
            check.outcome == "pass" for check in checks
            if check.command_category not in {"environment", "preview"}
        )
        if validation_passed and prepared is not None:
            try:
                preview_result = renderer.preview(prepared)
                if isinstance(preview_result, RendererCheckResult):
                    checks.append(preview_result)
                else:
                    checks.append(RendererCheckResult(
                        "renderer_preview", renderer.name, preview_result.exit_code,
                        "pass" if preview_result.exit_code == 0 else "fail", "preview",
                        preview_result.stderr_summary or preview_result.stdout_summary or "预览完成。",
                    ))
            except (OSError, RendererError, ValueError) as exc:
                checks.append(RendererCheckResult(
                    "renderer_preview", renderer.name, -1, "fail", "preview", str(exc),
                ))
            try:
                batch = renderer.render(prepared, plan, Path(asset_root))
            except (OSError, RendererError, ValueError) as exc:
                batch = RenderBatch((), tuple({
                    "motion_asset_id": item["motion_asset_id"],
                    "issue_type": "render_failed", "details": str(exc),
                } for item in plan["motion_assets"]))

    manifest_result = build_motion_asset_manifest(
        plan, str(plan["selected_renderer"]), batch,
        created_at=timestamp, manifest_id=chosen_manifest_id, probe_func=probe_func,
    )
    qa = prepare_production_qa(
        plan, manifest_result, created_at=timestamp, qa_id=chosen_qa_id,
        renderer_checks=checks,
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
        plan, ready_count=ready_count, failed_count=failed_count,
        preview_ready=any(
            asset["motion_asset_id"] == "MAPREVIEW" and asset["qa_status"] == "ready"
            for asset in manifest_result.manifest["assets"]
        ),
        motion_clip_ready_count=sum(
            1 for asset in manifest_result.manifest["assets"]
            if asset["asset_kind"] == "motion_clip" and asset["qa_status"] == "ready"
        ),
    )
    return ProductionWorkflowResult(
        plan, manifest_result.manifest, qa, plan_path, manifest_path, qa_path,
        prepared.project_dir if prepared else None, summary, environment,
    )
