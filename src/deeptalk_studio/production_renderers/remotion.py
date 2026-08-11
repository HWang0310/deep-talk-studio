"""Remotion adapter driven only by a validated Production Plan."""

import subprocess
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from .base import (
    CommandResult, PreparedProject, RenderBatch, RenderOutput, RendererError,
    prepare_project_directory, run_command, stage_plan_assets, write_json,
)
from ..production_storage import production_output_path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = REPO_ROOT / "renderer_templates" / "remotion"


class RemotionRenderer:
    name = "remotion"

    def __init__(self, template_root: Path = DEFAULT_TEMPLATE):
        self.template_root = Path(template_root)

    def prepare_project(
        self, plan: Mapping[str, Any], package: Any, profile: Mapping[str, Any],
        material_root: Path, projects_root: Path,
    ) -> PreparedProject:
        project = prepare_project_directory(
            self.template_root, projects_root, str(plan["production_id"]), self.name
        )
        staged, asset_map = stage_plan_assets(
            plan, package, material_root, project / "public" / "assets", prefix="assets"
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

    def validate_project(self, prepared: PreparedProject) -> Sequence[CommandResult]:
        install = self._install(prepared)
        lint = run_command(["npm", "run", "lint"], prepared.project_dir, timeout=600)
        compositions = run_command(
            ["npx", "remotion", "compositions", "src/index.ts"], prepared.project_dir, timeout=600
        )
        return (install, lint, compositions)

    def preview(self, prepared: PreparedProject, *, port: int = 3210) -> CommandResult:
        self._install(prepared)
        command = [
            "npx", "remotion", "studio", "src/index.ts", "--no-open",
            f"--port={port}", "--force-new",
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
                        return CommandResult(" ".join(command), 0, "".join(lines)[-4000:].strip(), "")
                if process.poll() is not None:
                    break
            raise RendererError("Remotion Studio 未能在 45 秒内提供 preview URL")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

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
                    "--codec=h264", "--log=error",
                ]
            elif expected["asset_kind"] == "rough_preview":
                command = [
                    "npx", "remotion", "render", "src/index.ts", "RoughPreview", str(path),
                    "--codec=h264", "--log=error",
                ]
            else:
                command = [
                    "npx", "remotion", "still", "src/index.ts", "HeroStill", str(path),
                    "--log=error",
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
