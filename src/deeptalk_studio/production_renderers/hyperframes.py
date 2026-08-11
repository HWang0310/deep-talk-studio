"""HyperFrames adapter with DESIGN.md-first deterministic HTML generation."""

import html
import json
import os
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from .base import (
    CommandResult, PreparedProject, RenderBatch, RenderOutput, RendererError,
    prepare_project_directory, run_command, stage_plan_assets, write_json,
)
from ..production_storage import production_output_path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = REPO_ROOT / "renderer_templates" / "hyperframes"
GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"


def hyperframes_browser_env(override: str = "") -> Mapping[str, str]:
    candidates = [
        override or os.environ.get("HYPERFRAMES_BROWSER_PATH", ""),
        os.environ.get("DEEPTALK_BROWSER_EXECUTABLE", ""),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return {"HYPERFRAMES_BROWSER_PATH": str(Path(candidate).resolve())}
    return {}


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _design(profile: Mapping[str, Any]) -> str:
    tokens = profile["design_tokens"]
    colors = tokens["colors"]
    typography = tokens["typography"]
    return f"""# DeepTalk Studio Production Identity 0.6

## Style Prompt

现代、克制、高信息密度的中文深度口播辅助视觉。真人露脸优先，动画短、明确、有目的；不用廉价科技蓝、霓虹堆叠或夸张转场。

## Colors

- Background: `{colors['background']}`
- Surface: `{colors['surface']}`
- Foreground: `{colors['foreground']}`
- Muted: `{colors['muted']}`
- Accent: `{colors['accent']}`

## Typography

- Display: `{typography['display']}`
- Body: `{typography['body']}`
- Data: `{typography['data']}`

## Motion

Use restrained, deterministic entrances. Build the final layout first. Timelines are paused and registered synchronously. No infinite repeats or random timing.

## What NOT to Do

- 不使用模板化 AI 蓝、紫蓝渐变或霓虹发光。
- 不把生成画面冒充新闻现场或真实文件。
- 不进行疯狂 zoom、无目的漂浮或随机动画。
- 不裁掉来源语境、免责声明和关键文字。
"""


def _scene_markup(scene: Mapping[str, Any], asset_map: Mapping[str, str], *, prefix: str) -> str:
    scene_id = _e(scene["scene_id"])
    asset_id = (scene["source_visual_ids"] or scene["source_material_ids"] or [""])[0]
    asset = asset_map.get(asset_id, "")
    image = f'<img class="scene-asset" src="{_e(prefix + asset)}" alt="" />' if asset else '<div class="aroll">真人口播</div>'
    text = "".join(
        f'<div class="screen-text text-{index}">{_e(entry["text"])}</div>'
        for index, entry in enumerate(scene["on_screen_text"][:4])
    )
    complete_class = " complete-generated-visual" if scene["source_visual_ids"] else ""
    return f'<div class="scene-content{complete_class}" id="content-{scene_id}">{image}<div class="text-stack">{text}</div><div class="source-note">来源：已批准 Research / Material Package</div></div>'


def _styles(profile: Mapping[str, Any]) -> str:
    t = profile["design_tokens"]
    c, f = t["colors"], t["typography"]
    return f"""
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: {c['background']}; color: {c['foreground']}; }}
body {{ font-family: \"{f['body']}\", serif; }}
.scene {{ position: absolute; inset: 0; overflow: hidden; background: {c['background']}; }}
.scene-content {{ width: 100%; height: 100%; padding: 100px 96px; display: flex; flex-direction: column; justify-content: center; gap: 24px; box-sizing: border-box; }}
.scene-asset {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }}
.aroll {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: {c['surface']}; font-family: \"{f['display']}\", sans-serif; font-size: 86px; font-weight: 900; }}
.text-stack {{ position: absolute; left: 96px; right: 96px; bottom: 100px; display: flex; flex-direction: column; align-items: flex-start; gap: 12px; }}
.screen-text {{ max-width: 1500px; padding: 10px 22px; background: {c['surface']}; color: {c['foreground']}; font-size: 34px; line-height: 1.3; }}
.text-0 {{ background: {c['accent']}; color: {c['background']}; font-family: \"{f['display']}\", sans-serif; font-size: 58px; font-weight: 900; letter-spacing: -0.03em; }}
.source-note {{ position: absolute; left: 96px; top: 70px; color: {c['muted']}; font-family: \"{f['data']}\", monospace; font-size: 22px; }}
.complete-generated-visual .text-stack, .complete-generated-visual .source-note {{ display: none; }}
"""


def _standalone_scene(
    scene: Mapping[str, Any], asset_map: Mapping[str, str], profile: Mapping[str, Any]
) -> str:
    duration = scene["duration_seconds"]
    scene_id = _e(scene["scene_id"])
    entrances = [
        f'tl.from("#content-{scene_id} .scene-asset, #content-{scene_id} .aroll", {{ opacity: 0, scale: 0.97, duration: 0.65, ease: "power3.out" }}, 0.2);',
        f'tl.from("#content-{scene_id} .text-0", {{ opacity: 0, x: -42, duration: 0.48, ease: "expo.out" }}, 0.38);',
        f'tl.from("#content-{scene_id} .screen-text:not(.text-0)", {{ opacity: 0, y: 28, duration: 0.36, stagger: 0.12, ease: "sine.out" }}, 0.58);',
        f'tl.from("#content-{scene_id} .source-note", {{ opacity: 0, duration: 0.3, ease: "power1.out" }}, 0.72);',
    ]
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/><script src="{GSAP_CDN}"></script><style>{_styles(profile)}</style></head><body>
<div id="root-{scene_id}" data-composition-id="scene-{scene_id}" data-start="0" data-duration="{duration}" data-width="1920" data-height="1080" data-fps="30"><div class="scene">{_scene_markup(scene, asset_map, prefix="")}</div></div>
<script>window.__timelines = window.__timelines || {{}}; const tl = gsap.timeline({{ paused: true }}); {''.join(entrances)} window.__timelines["scene-{scene_id}"] = tl;</script></body></html>'''


def _rough_preview(plan: Mapping[str, Any], asset_map: Mapping[str, str], profile: Mapping[str, Any]) -> str:
    cursor = 0.0
    clips, timeline = [], []
    previous = ""
    for index, scene in enumerate(plan["scenes"]):
        scene_id = _e(scene["scene_id"])
        duration = float(scene["duration_seconds"])
        opacity = "1" if index == 0 else "0"
        clips.append(
            f'<div id="scene-{scene_id}" class="scene clip" data-start="{cursor:.3f}" data-duration="{duration:.3f}" data-track-index="{index % 2 + 1}" style="opacity:{opacity}">{_scene_markup(scene, asset_map, prefix="")}</div>'
        )
        start = cursor
        if index > 0:
            transition = max(0.0, start - 0.4)
            timeline.append(f'tl.to("#scene-{previous}", {{ opacity: 0, duration: 0.4, ease: "power2.inOut" }}, {transition:.3f}).to("#scene-{scene_id}", {{ opacity: 1, duration: 0.4, ease: "power2.inOut" }}, "<");')
        timeline.extend([
            f'tl.from("#content-{scene_id} .scene-asset, #content-{scene_id} .aroll", {{ opacity: 0, scale: 0.97, duration: 0.65, ease: "power3.out" }}, {start + 0.2:.3f});',
            f'tl.from("#content-{scene_id} .text-0", {{ opacity: 0, x: -42, duration: 0.48, ease: "expo.out" }}, {start + 0.38:.3f});',
            f'tl.from("#content-{scene_id} .screen-text:not(.text-0)", {{ opacity: 0, y: 28, duration: 0.36, stagger: 0.12, ease: "sine.out" }}, {start + 0.58:.3f});',
            f'tl.from("#content-{scene_id} .source-note", {{ opacity: 0, duration: 0.3, ease: "power1.out" }}, {start + 0.72:.3f});',
        ])
        previous = scene_id
        cursor += duration
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/><script src="{GSAP_CDN}"></script><style>{_styles(profile)}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{cursor:.3f}" data-width="1920" data-height="1080" data-fps="30">{''.join(clips)}</div>
<script>window.__timelines = window.__timelines || {{}}; const tl = gsap.timeline({{ paused: true }}); {''.join(timeline)} window.__timelines["main"] = tl;</script></body></html>'''


class HyperFramesRenderer:
    name = "hyperframes"

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
            plan, package, material_root, project / "assets", prefix="assets"
        )
        plan_path = project / "production-plan.json"
        write_json(plan_path, plan)
        write_json(project / "production-profile.json", profile)
        write_json(project / "asset-map.json", asset_map)
        # HyperFrames visual identity hard gate: DESIGN.md is created before any composition HTML.
        (project / "DESIGN.md").write_text(_design(profile), encoding="utf-8")
        compositions = project / "compositions"
        compositions.mkdir(parents=True, exist_ok=True)
        for scene in plan["scenes"]:
            (compositions / f'{scene["scene_id"]}.html').write_text(
                _standalone_scene(scene, asset_map, profile), encoding="utf-8"
            )
        (project / "index.html").write_text(
            _rough_preview(plan, asset_map, profile), encoding="utf-8"
        )
        return PreparedProject(self.name, project, plan_path, staged)

    def _install(self, prepared: PreparedProject) -> CommandResult:
        if (prepared.project_dir / "node_modules").is_dir():
            return CommandResult("npm ci (cached)", 0, "node_modules 已存在", "")
        return run_command(["npm", "ci", "--no-audit", "--no-fund"], prepared.project_dir, timeout=1800)

    def validate_project(self, prepared: PreparedProject) -> Sequence[CommandResult]:
        install = self._install(prepared)
        doctor = run_command(["npx", "hyperframes", "doctor"], prepared.project_dir, timeout=600)
        lint = run_command(["npx", "hyperframes", "lint", "."], prepared.project_dir, timeout=600)
        validate = run_command(["npx", "hyperframes", "validate", "."], prepared.project_dir, timeout=600)
        inspect = run_command(["npx", "hyperframes", "inspect", ".", "--samples", "8"], prepared.project_dir, timeout=900)
        return (install, doctor, lint, validate, inspect)

    def preview(self, prepared: PreparedProject, *, port: int = 3211) -> CommandResult:
        self._install(prepared)
        start = run_command(
            ["npx", "hyperframes", "preview", ".", f"--port={port}", "--background", "--no-open"],
            prepared.project_dir, timeout=120,
        )
        status = run_command(
            ["npx", "hyperframes", "preview", ".", "--status"], prepared.project_dir, timeout=120
        )
        run_command(["npx", "hyperframes", "preview", ".", "--stop"], prepared.project_dir, timeout=120)
        return CommandResult(
            start.command_summary, 0,
            (start.stdout_summary + "\n" + status.stdout_summary).strip(), "",
        )

    def render(
        self, prepared: PreparedProject, plan: Mapping[str, Any], output_root: Path,
    ) -> RenderBatch:
        self._install(prepared)
        outputs, failures = [], []
        rough_output = None
        for expected in plan["motion_assets"]:
            path = production_output_path(
                output_root, str(plan["production_id"]), expected["motion_asset_id"],
                expected["requested_format"],
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            if expected["asset_kind"] == "hero_still":
                if rough_output is None:
                    failures.append({
                        "motion_asset_id": expected["motion_asset_id"],
                        "issue_type": "render_failed",
                        "details": "HyperFrames hero still 需要先完成 rough preview",
                    })
                    continue
                command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", "0.5",
                           "-i", str(rough_output), "-frames:v", "1", str(path)]
            else:
                command = [
                    "npx", "hyperframes", "render", ".", "--output", str(path),
                    "--fps", "30", "--quality", "draft", "--workers", "1", "--strict",
                ]
                if expected["asset_kind"] == "motion_clip":
                    command.extend(["--composition", f'compositions/{expected["scene_id"]}.html'])
                else:
                    rough_output = path
            try:
                result = run_command(
                    command, prepared.project_dir, timeout=1800,
                    env=hyperframes_browser_env(),
                )
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
