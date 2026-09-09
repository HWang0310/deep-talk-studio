"""Shared subprocess, project and asset boundary for production renderers."""

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

from ..production_storage import SAFE_ID
from ..production_validation import validate_render_asset


class RendererError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    command_summary: str
    exit_code: int
    stdout_summary: str
    stderr_summary: str


@dataclass(frozen=True)
class RendererCheckResult:
    check_name: str
    renderer: str
    exit_code: int
    outcome: str
    command_category: str
    summary: str

    def to_dict(self) -> Mapping[str, Any]:
        return {
            "check_name": self.check_name, "renderer": self.renderer,
            "exit_code": self.exit_code, "outcome": self.outcome,
            "command_category": self.command_category, "summary": self.summary,
        }


@dataclass(frozen=True)
class PreparedProject:
    renderer: str
    project_dir: Path
    plan_path: Path
    staged_assets: Tuple[Path, ...]


@dataclass(frozen=True)
class RenderOutput:
    motion_asset_id: str
    scene_id: str
    asset_kind: str
    output_path: Path
    command_summary: str


@dataclass(frozen=True)
class RenderBatch:
    outputs: Tuple[RenderOutput, ...]
    failures: Tuple[Mapping[str, str], ...]


def _summary(text: str, limit: int = 4000) -> str:
    clean = str(text).strip()
    return clean[-limit:] if len(clean) > limit else clean


def safe_check_summary(text: str, cwd: Path) -> str:
    clean = _summary(text, 1200)
    candidates = {str(cwd), str(Path(cwd).resolve()), str(Path.home()), str(Path.home().resolve())}
    for candidate in sorted((value for value in candidates if value), key=len, reverse=True):
        clean = clean.replace(candidate, "<project>" if candidate in {str(cwd), str(Path(cwd).resolve())} else "<home>")
    clean = re.sub(r"https?://(?:localhost|127\.0\.0\.1|(?:\d{1,3}\.){3}\d{1,3})[^\s,]*", "<local-preview>", clean)
    return clean or "检查完成。"


def run_command(
    command: Sequence[str], cwd: Path, *, timeout: int = 600,
    env: Mapping[str, str] = None,
) -> CommandResult:
    command_env = os.environ.copy()
    if env:
        command_env.update({str(key): str(value) for key, value in env.items()})
    try:
        completed = subprocess.run(
            list(command), cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, check=False, env=command_env,
        )
    except FileNotFoundError as exc:
        raise RendererError(f"制作环境缺少命令：{command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RendererError(f"Renderer 执行超时：{' '.join(command[:4])}") from exc
    result = CommandResult(
        " ".join(str(part) for part in command), completed.returncode,
        _summary(completed.stdout), _summary(completed.stderr),
    )
    if completed.returncode != 0:
        detail = result.stderr_summary or result.stdout_summary or "没有错误摘要"
        raise RendererError(
            f"Renderer 命令执行失败（exit {completed.returncode}）：{detail}"
        )
    return result


def run_renderer_check(
    check_name: str, renderer: str, command_category: str,
    command: Sequence[str], cwd: Path, *, timeout: int = 600,
    env: Mapping[str, str] = None,
) -> RendererCheckResult:
    """Run one QA command without erasing its exit outcome on failure."""

    command_env = os.environ.copy()
    if env:
        command_env.update({str(key): str(value) for key, value in env.items()})
    try:
        completed = subprocess.run(
            list(command), cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, check=False, env=command_env,
        )
        summary = safe_check_summary(completed.stderr or completed.stdout or "检查完成。", cwd)
        return RendererCheckResult(
            check_name, renderer, completed.returncode,
            "pass" if completed.returncode == 0 else "fail",
            command_category, summary,
        )
    except FileNotFoundError:
        return RendererCheckResult(check_name, renderer, 127, "fail", command_category, f"缺少命令：{command[0]}")
    except subprocess.TimeoutExpired:
        return RendererCheckResult(check_name, renderer, 124, "fail", command_category, "命令执行超时。")


def prepare_project_directory(
    template_root: Path, projects_root: Path, production_id: str, renderer: str
) -> Path:
    if not SAFE_ID.fullmatch(str(production_id)):
        raise RendererError("Production ID 无效，拒绝创建 renderer 项目")
    target = (Path(projects_root).resolve() / production_id / renderer).resolve()
    root = Path(projects_root).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise RendererError("Renderer project 路径越界") from None
    if target.exists():
        raise RendererError("Renderer project 已存在，拒绝覆盖")
    shutil.copytree(template_root, target, ignore=shutil.ignore_patterns("node_modules", ".git"))
    return target


def stage_plan_assets(
    plan: Mapping[str, Any], package: Any, material_root: Path,
    destination: Path, *, prefix: str, artifact_resolver=None,
) -> Tuple[Tuple[Path, ...], Mapping[str, str]]:
    materials = {item["material_id"]: item for item in package.materials}
    visuals = {item["visual_id"]: item for item in package.generated_visuals}
    selected = []
    for scene in plan["scenes"]:
        selected.extend((item_id, materials[item_id], False) for item_id in scene["source_material_ids"])
        # Four semantic motion types are rebuilt from scene_payload. Their V0.5 SVG is
        # provenance/debug fallback only and must not become a whole-image animation.
        if scene.get("scene_payload", {}).get("payload_type") not in {
            "timeline", "bar", "comparison", "diagram",
        }:
            selected.extend((item_id, visuals[item_id], True) for item_id in scene["source_visual_ids"])
    destination.mkdir(parents=True, exist_ok=True)
    staged, asset_map = [], {}
    for item_id, item, generated in selected:
        if item_id in asset_map:
            continue
        source = validate_render_asset(
            item, material_root, generated_visual=generated,
            artifact_resolver=artifact_resolver, package_id=package.package_id,
        )
        target = destination / f"{item_id}{source.suffix.casefold()}"
        if target.exists():
            raise RendererError("Renderer asset 已存在，拒绝覆盖")
        shutil.copyfile(source, target)
        staged.append(target)
        asset_map[item_id] = f"{prefix}/{target.name}"
    return tuple(staged), asset_map


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
