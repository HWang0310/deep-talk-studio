"""HyperFrames adapter consuming only validated Production 0.6.1 scene payloads."""

import html
import os
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from .base import (
    CommandResult, PreparedProject, RenderBatch, RenderOutput, RendererCheckResult,
    RendererError, prepare_project_directory, run_command, run_renderer_check,
    stage_plan_assets, write_json,
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
        shutil.which("google-chrome") or "", shutil.which("chromium") or "",
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
    return f"""# DeepTalk Studio Production Identity 0.6.1

## Style Prompt

现代、克制、高信息密度的中文深度口播辅助视觉。真人露脸优先，动画短、明确、有目的。

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

Layout first. Paused synchronous timelines only. No random timing, async registration or infinite repeats.

## What NOT to Do

- 不使用霓虹堆叠或无目的漂浮。
- 不把生成画面冒充新闻现场或真实文件。
- 不裁掉来源语境、免责声明和关键文字。
"""


def _styles(profile: Mapping[str, Any]) -> str:
    token = profile["design_tokens"]
    color, font = token["colors"], token["typography"]
    return f"""
* {{ box-sizing:border-box; }} html,body {{ margin:0; width:1920px; height:1080px; overflow:hidden; background:{color['background']}; color:{color['foreground']}; }}
body {{ font-family:"{font['body']}",serif; }} .scene {{ position:absolute; inset:0; overflow:hidden; background:{color['background']}; }}
.scene-content {{ position:absolute; inset:0; }} .motion-heading {{ position:absolute; left:96px; top:70px; font:900 58px "{font['display']}"; z-index:5; }}
.source-note {{ position:absolute; right:96px; top:76px; color:{color['muted']}; font:22px "{font['data']}"; }}
.aroll {{ position:absolute; inset:100px 96px; display:flex; align-items:center; justify-content:center; background:{color['surface']}; font:900 86px "{font['display']}"; }}
.scene-asset {{ position:absolute; inset:0; width:100%; height:100%; object-fit:contain; }}
.timeline {{ position:absolute; left:180px; right:180px; top:500px; height:360px; }} .timeline-baseline {{ position:absolute; top:40px; left:0; right:0; height:8px; background:{color['muted']}; }}
.timeline-marker {{ position:absolute; top:18px; width:360px; margin-left:-180px; text-align:center; }} .marker-dot {{ width:44px; height:44px; margin:0 auto; border-radius:50%; background:{color['accent']}; }} .marker-date {{ margin-top:-100px; color:{color['accent']}; font:28px "{font['data']}"; }} .marker-label {{ margin-top:86px; font-size:30px; line-height:1.35; }}
.bar-chart {{ position:absolute; left:180px; right:180px; bottom:150px; height:610px; border-bottom:5px solid {color['muted']}; display:flex; align-items:flex-end; justify-content:space-around; }} .bar-item {{ width:240px; text-align:center; display:flex; flex-direction:column; align-items:center; }} .bar-column {{ width:150px; background:{color['accent']}; border-radius:10px 10px 0 0; }} .bar-value,.bar-label {{ font-size:29px; margin:10px 0; }}
.comparison {{ position:absolute; left:120px; right:120px; top:210px; bottom:100px; display:flex; flex-direction:column; gap:24px; }} .comparison-item {{ display:grid; grid-template-columns:1fr 1fr; gap:34px; }} .comparison-side {{ padding:26px; background:{color['surface']}; border-left:8px solid {color['accent']}; font-size:31px; line-height:1.4; }} .comparison-side.right {{ border-color:{color['muted']}; }}
.diagram {{ position:absolute; inset:0; }} .diagram line {{ stroke:{color['muted']}; stroke-width:6; }} .diagram rect {{ fill:{color['surface']}; stroke:{color['accent']}; stroke-width:5; }} .diagram text {{ fill:{color['foreground']}; font:29px "{font['body']}"; text-anchor:middle; }}
.capture-highlight {{ position:absolute; left:180px; right:180px; bottom:130px; height:180px; border:4px solid {color['accent']}; }}
"""


def _scene_markup(scene: Mapping[str, Any], asset_map: Mapping[str, str], *, prefix: str) -> str:
    scene_id = _e(scene["scene_id"])
    payload = scene["scene_payload"]
    kind = payload["payload_type"]
    heading = _e(scene["on_screen_text"][0]["text"] if scene["on_screen_text"] else "")
    body = ""
    if kind == "timeline":
        events = payload["timeline_events"]
        markers = []
        for index, event in enumerate(events):
            left = 50 if len(events) == 1 else 8 + index * 84 / (len(events) - 1)
            markers.append(
                f'<div id="timeline-marker-{index + 1}-{scene_id}" class="timeline-marker" data-motion-element="timeline-marker" style="left:{left:.3f}%">'
                f'<div class="marker-dot"></div><div class="marker-date">{_e(event["date"]["text"])}</div><div class="marker-label">{_e(event["label"]["text"])}</div></div>'
            )
        body = f'<div class="timeline"><div class="timeline-baseline" data-motion-element="timeline-baseline"></div>{"".join(markers)}</div>'
    elif kind == "bar":
        points = payload["bar_data_points"]
        maximum = max([abs(float(point["value"])) for point in points] or [1.0])
        body = '<div class="bar-chart">' + "".join(
            f'<div class="bar-item" data-motion-element="bar"><div class="bar-value">{_e(point["value_label"]["text"])}</div><div class="bar-column" style="height:{470 * abs(float(point["value"])) / maximum:.2f}px"></div><div class="bar-label">{_e(point["label"]["text"])}</div></div>'
            for point in points
        ) + '</div>'
    elif kind == "comparison":
        body = '<div class="comparison">' + "".join(
            f'<div class="comparison-item" data-motion-element="comparison-item"><div class="comparison-side left"><strong>{_e(item["label"]["text"])}</strong><br>{_e(item["left_text"]["text"])}</div><div class="comparison-side right"><strong>{_e(item["label"]["text"])}</strong><br>{_e(item["right_text"]["text"])}</div></div>'
            for item in payload["comparison_items"]
        ) + '</div>'
    elif kind == "diagram":
        nodes = payload["diagram_nodes"]
        positions = {node["node_id"]: (330 + index * (1260 / max(1, len(nodes) - 1)), 550 + (120 if index % 2 else -120)) for index, node in enumerate(nodes)}
        edges = "".join(
            f'<g id="diagram-edge-{edge["order"]}-{scene_id}" data-motion-element="diagram-edge"><line x1="{positions[edge["from_node"]][0]:.2f}" y1="{positions[edge["from_node"]][1]:.2f}" x2="{positions[edge["to_node"]][0]:.2f}" y2="{positions[edge["to_node"]][1]:.2f}"/><text x="{(positions[edge["from_node"]][0] + positions[edge["to_node"]][0]) / 2:.2f}" y="{(positions[edge["from_node"]][1] + positions[edge["to_node"]][1]) / 2 - 18:.2f}">{_e(edge["label"]["text"])}</text></g>' for edge in payload["diagram_edges"]
        )
        rendered_nodes = "".join(
            f'<g id="diagram-node-{node["order"]}-{scene_id}" data-motion-element="diagram-node"><rect x="{positions[node["node_id"]][0] - 150:.2f}" y="{positions[node["node_id"]][1] - 65:.2f}" width="300" height="130" rx="18"/><text x="{positions[node["node_id"]][0]:.2f}" y="{positions[node["node_id"]][1] + 10:.2f}">{_e(node["label"]["text"])}</text></g>' for node in nodes
        )
        body = f'<svg class="diagram" width="1920" height="1080">{edges}{rendered_nodes}</svg>'
    elif kind == "image":
        asset = asset_map.get(payload["image_asset_id"], "")
        body = f'<img class="scene-asset" src="{_e(prefix + asset)}" alt="" />' if asset else ""
        if payload["capture_region"]:
            body += '<div class="capture-highlight" data-motion-element="capture-highlight"></div>'
    else:
        body = '<div class="aroll">真人口播</div>'
    return f'<div class="scene-content" id="content-{scene_id}"><div class="motion-heading">{heading}</div>{body}<div class="source-note">来源：已批准 Research / Material Package</div></div>'


def _scene_timeline(scene: Mapping[str, Any], offset: float = 0.0) -> str:
    scene_id = _e(scene["scene_id"])
    payload = scene["scene_payload"]
    commands = [f'tl.from("#content-{scene_id} .motion-heading", {{ opacity: 0, x: -36, duration: 0.42, ease: "expo.out" }}, {offset + 0.12:.3f});']
    kind = payload["payload_type"]
    if kind == "timeline":
        commands.append(f'tl.from("#content-{scene_id} .timeline-baseline", {{ scaleX: 0, transformOrigin: "left center", duration: 0.62, ease: "power3.out" }}, {offset + 0.28:.3f});')
        for index, _ in enumerate(payload["timeline_events"], 1):
            commands.append(f'tl.from("#timeline-marker-{index}-{scene_id}", {{ opacity: 0, y: 20, scale: 0.8, duration: 0.36, ease: "back.out(1.5)" }}, {offset + 0.72 + (index - 1) * 0.24:.3f});')
    elif kind == "bar":
        commands.append(f'tl.from("#content-{scene_id} .bar-column", {{ scaleY: 0, transformOrigin: "center bottom", duration: 0.62, stagger: 0.18, ease: "power3.out" }}, {offset + 0.35:.3f});')
        commands.append(f'tl.from("#content-{scene_id} .bar-value, #content-{scene_id} .bar-label", {{ opacity: 0, y: 16, duration: 0.3, stagger: 0.09, ease: "sine.out" }}, {offset + 0.78:.3f});')
    elif kind == "comparison":
        commands.append(f'tl.from("#content-{scene_id} .comparison-item", {{ opacity: 0, x: 42, duration: 0.46, stagger: 0.2, ease: "power3.out" }}, {offset + 0.34:.3f});')
    elif kind == "diagram":
        for node in payload["diagram_nodes"]:
            commands.append(f'tl.from("#diagram-node-{node["order"]}-{scene_id}", {{ opacity: 0, scale: 0.82, transformOrigin: "center", duration: 0.38, ease: "back.out(1.4)" }}, {offset + 0.28 + (node["order"] - 1) * 0.24:.3f});')
        node_order = {node["node_id"]: node["order"] for node in payload["diagram_nodes"]}
        for edge in payload["diagram_edges"]:
            start = offset + 0.42 + max(node_order[edge["from_node"]], node_order[edge["to_node"]]) * 0.24 + (edge["order"] - 1) * 0.16
            commands.append(f'tl.from("#diagram-edge-{edge["order"]}-{scene_id}", {{ opacity: 0, duration: 0.36, ease: "sine.out" }}, {start:.3f});')
    elif kind == "image":
        commands.append(f'tl.fromTo("#content-{scene_id} .scene-asset", {{ scale: 1, x: 0 }}, {{ scale: 1.035, x: -12, duration: 3, ease: "none" }}, {offset:.3f});')
        commands.append(f'tl.from("#content-{scene_id} .capture-highlight", {{ opacity: 0, duration: 0.4, ease: "power2.out" }}, {offset + 0.55:.3f});')
    else:
        commands.append(f'tl.from("#content-{scene_id} .aroll", {{ opacity: 0, scale: 0.98, duration: 0.5, ease: "power3.out" }}, {offset + 0.15:.3f});')
    return "".join(commands)


def _standalone_scene(scene: Mapping[str, Any], asset_map: Mapping[str, str], profile: Mapping[str, Any]) -> str:
    scene_id = _e(scene["scene_id"])
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/><script src="{GSAP_CDN}"></script><style>{_styles(profile)}</style></head><body><div id="root-{scene_id}" data-composition-id="scene-{scene_id}" data-start="0" data-duration="{scene["duration_seconds"]}" data-width="1920" data-height="1080" data-fps="30"><div class="scene">{_scene_markup(scene, asset_map, prefix="")}</div></div><script>window.__timelines = window.__timelines || {{}}; const tl = gsap.timeline({{ paused: true }}); {_scene_timeline(scene)} window.__timelines["scene-{scene_id}"] = tl;</script></body></html>'''


def _rough_preview(plan: Mapping[str, Any], asset_map: Mapping[str, str], profile: Mapping[str, Any]) -> str:
    cursor = 0.0
    clips, timeline = [], []
    for index, scene in enumerate(plan["scenes"]):
        scene_id = _e(scene["scene_id"])
        duration = float(scene["duration_seconds"])
        clips.append(f'<div id="scene-{scene_id}" class="scene clip" data-start="{cursor:.3f}" data-duration="{duration:.3f}" data-track-index="{index % 2 + 1}">{_scene_markup(scene, asset_map, prefix="")}</div>')
        if index > 0:
            timeline.append(f'tl.from("#scene-{scene_id}", {{ xPercent: 100, duration: 0.4, ease: "power2.inOut" }}, {cursor:.3f});')
        timeline.append(_scene_timeline(scene, cursor))
        cursor += duration
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1920, height=1080"/><script src="{GSAP_CDN}"></script><style>{_styles(profile)}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{cursor:.3f}" data-width="1920" data-height="1080" data-fps="30">{"".join(clips)}</div><script>window.__timelines = window.__timelines || {{}}; const tl = gsap.timeline({{ paused: true }}); {"".join(timeline)} window.__timelines["main"] = tl;</script></body></html>'''


class HyperFramesRenderer:
    name = "hyperframes"

    def __init__(self, template_root: Path = DEFAULT_TEMPLATE):
        self.template_root = Path(template_root)

    def prepare_project(self, plan: Mapping[str, Any], package: Any, profile: Mapping[str, Any], material_root: Path, projects_root: Path) -> PreparedProject:
        project = prepare_project_directory(self.template_root, projects_root, str(plan["production_id"]), self.name)
        staged, asset_map = stage_plan_assets(plan, package, material_root, project / "assets", prefix="assets")
        plan_path = project / "production-plan.json"
        write_json(plan_path, plan); write_json(project / "production-profile.json", profile); write_json(project / "asset-map.json", asset_map)
        (project / "DESIGN.md").write_text(_design(profile), encoding="utf-8")
        compositions = project / "compositions"; compositions.mkdir(parents=True, exist_ok=True)
        for scene in plan["scenes"]:
            (compositions / f'{scene["scene_id"]}.html').write_text(_standalone_scene(scene, asset_map, profile), encoding="utf-8")
        (project / "index.html").write_text(_rough_preview(plan, asset_map, profile), encoding="utf-8")
        return PreparedProject(self.name, project, plan_path, staged)

    def _install(self, prepared: PreparedProject) -> CommandResult:
        if (prepared.project_dir / "node_modules").is_dir():
            return CommandResult("npm ci (cached)", 0, "node_modules 已存在", "")
        return run_command(["npm", "ci", "--no-audit", "--no-fund"], prepared.project_dir, timeout=1800)

    def validate_project(self, prepared: PreparedProject) -> Sequence[RendererCheckResult]:
        checks = (
            ("hyperframes_npm_ci", "install", ["npm", "ci", "--no-audit", "--no-fund"], 1800),
            ("hyperframes_doctor", "doctor", ["npx", "hyperframes", "doctor"], 600),
            ("hyperframes_lint", "lint", ["npx", "hyperframes", "lint", "."], 600),
            ("hyperframes_validate", "validate", ["npx", "hyperframes", "validate", "."], 600),
            ("hyperframes_inspect", "inspect", ["npx", "hyperframes", "inspect", ".", "--samples", "8"], 900),
        )
        return tuple(
            run_renderer_check(name, self.name, category, command, prepared.project_dir, timeout=timeout)
            for name, category, command, timeout in checks
        )

    def preview(self, prepared: PreparedProject, *, port: int = 3211) -> RendererCheckResult:
        start = run_renderer_check(
            "hyperframes_preview", self.name, "preview",
            ["npx", "hyperframes", "preview", ".", f"--port={port}", "--background", "--no-open"],
            prepared.project_dir, timeout=120,
        )
        if start.outcome == "pass":
            status = run_renderer_check(
                "hyperframes_preview_status", self.name, "preview",
                ["npx", "hyperframes", "preview", ".", "--status"], prepared.project_dir, timeout=120,
            )
            run_renderer_check(
                "hyperframes_preview_stop", self.name, "preview",
                ["npx", "hyperframes", "preview", ".", "--stop"], prepared.project_dir, timeout=120,
            )
            if status.outcome == "fail":
                return RendererCheckResult("hyperframes_preview", self.name, status.exit_code, "fail", "preview", status.summary)
        return start

    def render(self, prepared: PreparedProject, plan: Mapping[str, Any], output_root: Path) -> RenderBatch:
        self._install(prepared); outputs, failures, rough_output = [], [], None
        for expected in plan["motion_assets"]:
            path = production_output_path(output_root, str(plan["production_id"]), expected["motion_asset_id"], expected["requested_format"]); path.parent.mkdir(parents=True, exist_ok=True)
            if expected["asset_kind"] == "hero_still":
                if rough_output is None:
                    failures.append({"motion_asset_id": expected["motion_asset_id"], "issue_type": "render_failed", "details": "HyperFrames hero still 需要先完成 rough preview"}); continue
                command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", "0.5", "-i", str(rough_output), "-frames:v", "1", str(path)]
            else:
                command = ["npx", "hyperframes", "render", ".", "--output", str(path), "--fps", "30", "--quality", "draft", "--workers", "1", "--strict"]
                if expected["asset_kind"] == "motion_clip": command.extend(["--composition", f'compositions/{expected["scene_id"]}.html'])
                else: rough_output = path
            try:
                result = run_command(command, prepared.project_dir, timeout=1800, env=hyperframes_browser_env())
                outputs.append(RenderOutput(expected["motion_asset_id"], expected["scene_id"], expected["asset_kind"], path, result.command_summary))
            except RendererError as exc:
                failures.append({"motion_asset_id": expected["motion_asset_id"], "issue_type": "render_failed", "details": str(exc)})
        return RenderBatch(tuple(outputs), tuple(failures))
