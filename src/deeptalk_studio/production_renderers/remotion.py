"""Remotion adapter driven only by a validated Production Plan."""

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .base import (
    CommandResult, PreparedProject, RenderBatch, RenderOutput, RendererCheckResult,
    RendererError, prepare_project_directory, run_command, run_renderer_check,
    safe_check_summary, stage_plan_assets, write_json,
)
from ..production_storage import production_output_path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = REPO_ROOT / "renderer_templates" / "remotion"


def browser_executable_args(override: str = "") -> tuple:
    """Prefer an installed Chromium browser over a slow first-run download."""

    candidates = [
        override or os.environ.get("DEEPTALK_BROWSER_EXECUTABLE", ""),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return (f"--browser-executable={Path(candidate).resolve()}",)
    return ()


class RemotionRenderer:
    name = "remotion"

    def __init__(self, template_root: Path = DEFAULT_TEMPLATE):
        self.template_root = Path(template_root)

    def prepare_project(
        self, plan: Mapping[str, Any], package: Any, profile: Mapping[str, Any],
        material_root: Path, projects_root: Path, *, artifact_resolver=None,
    ) -> PreparedProject:
        project = prepare_project_directory(
            self.template_root, projects_root, str(plan["production_id"]), self.name
        )
        staged, asset_map = stage_plan_assets(
            plan, package, material_root, project / "public" / "assets",
            prefix="assets", artifact_resolver=artifact_resolver,
        )
        plan_path = project / "src" / "production-plan.json"
        write_json(plan_path, plan)
        write_json(project / "src" / "production-profile.json", profile)
        write_json(project / "src" / "asset-map.json", asset_map)
        return PreparedProject(self.name, project, plan_path, staged)

    def _install(self, prepared: PreparedProject) -> CommandResult:
        if (prepared.project_dir / "node_modules").is_dir():
            return CommandResult("npm ci (cached)", 0, "node_modules 已存在", "")
        return run_command(["npm", "ci", "--no-audit", "--no-fund"], prepared.project_dir, timeout=1200)

    def validate_project(self, prepared: PreparedProject) -> Sequence[RendererCheckResult]:
        install = run_renderer_check(
            "remotion_npm_ci", self.name, "install",
            ["npm", "ci", "--no-audit", "--no-fund"], prepared.project_dir, timeout=1200,
        )
        lint = run_renderer_check(
            "remotion_lint", self.name, "lint", ["npm", "run", "lint"],
            prepared.project_dir, timeout=600,
        )
        typecheck = run_renderer_check(
            "remotion_typecheck", self.name, "typecheck", ["npm", "run", "typecheck"],
            prepared.project_dir, timeout=600,
        )
        compositions = run_renderer_check(
            "remotion_compositions", self.name, "compositions",
            ["npx", "remotion", "compositions", "src/index.ts",
             f"--public-dir={prepared.project_dir / 'public'}", *browser_executable_args()],
            prepared.project_dir, timeout=600,
        )
        return (install, lint, typecheck, compositions)

    def preview(self, prepared: PreparedProject, *, port: int = 3210) -> RendererCheckResult:
        command = [
            "npx", "remotion", "studio", "src/index.ts", "--no-open",
            f"--port={port}", "--force-new",
            f"--public-dir={prepared.project_dir / 'public'}", *browser_executable_args(),
        ]
        process = subprocess.Popen(
            command, cwd=str(prepared.project_dir), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
        )
        lines = []
        deadline = time.time() + 45
        try:
            while time.time() < deadline:
                line = process.stdout.readline() if process.stdout else ""
                if line:
                    lines.append(line)
                    if "http://" in line or "localhost:" in line:
                        return RendererCheckResult(
                            "remotion_preview", self.name, 0, "pass", "preview",
                            safe_check_summary("".join(lines), prepared.project_dir),
                        )
                if process.poll() is not None:
                    break
            return RendererCheckResult(
                "remotion_preview", self.name, process.returncode or -1,
                "fail", "preview", "Remotion Studio 未能提供 preview URL。",
            )
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            if process.stdout is not None:
                process.stdout.close()

    def render(
        self, prepared: PreparedProject, plan: Mapping[str, Any], output_root: Path,
    ) -> RenderBatch:
        self._install(prepared)
        outputs, failures = [], []
        for expected in plan["motion_assets"]:
            path = production_output_path(
                output_root, str(plan["production_id"]), expected["motion_asset_id"],
                expected["requested_format"],
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            if expected["asset_kind"] == "motion_clip":
                composition = f'Scene-{expected["scene_id"]}'
                command = [
                    "npx", "remotion", "render", "src/index.ts", composition, str(path),
                    "--codec=h264", "--concurrency=1", "--log=error",
                    f"--public-dir={prepared.project_dir / 'public'}", *browser_executable_args(),
                ]
            elif expected["asset_kind"] == "rough_preview":
                command = [
                    "npx", "remotion", "render", "src/index.ts", "RoughPreview", str(path),
                    "--codec=h264", "--concurrency=1", "--log=error",
                    f"--public-dir={prepared.project_dir / 'public'}", *browser_executable_args(),
                ]
            else:
                command = [
                    "npx", "remotion", "still", "src/index.ts", "HeroStill", str(path),
                    "--log=error", f"--public-dir={prepared.project_dir / 'public'}",
                    *browser_executable_args(),
                ]
            try:
                result = run_command(command, prepared.project_dir, timeout=1200)
                outputs.append(RenderOutput(
                    expected["motion_asset_id"], expected["scene_id"], expected["asset_kind"],
                    path, result.command_summary,
                ))
            except RendererError as exc:
                failures.append({
                    "motion_asset_id": expected["motion_asset_id"],
                    "issue_type": "render_failed", "details": str(exc),
                })
        return RenderBatch(tuple(outputs), tuple(failures))
