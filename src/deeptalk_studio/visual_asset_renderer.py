"""Binding-first browser renderer for Visual Asset Engine MVP text assets."""
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .motion_spec import MotionSpecError, assert_renderable


class VisualAssetRenderError(ValueError):
    pass


CANVAS = {"width": 1920, "height": 1080, "fps": 30}
FONT_CANDIDATES = (
    ("Hiragino Sans GB", Path("/System/Library/Fonts/Hiragino Sans GB.ttc")),
    ("PingFang SC", Path("/System/Library/Fonts/PingFang.ttc")),
)
TEXT_STYLES = {
    "title": {"font_size": 58, "max_lines": 2, "weight": 900},
    "heading": {"font_size": 40, "max_lines": 2, "weight": 800},
    "body": {"font_size": 31, "max_lines": 2, "weight": 600},
    "numeric": {"font_size": 42, "max_lines": 1, "weight": 900},
}


def _font_family():
    for family, path in FONT_CANDIDATES:
        if path.is_file():
            return family
    raise VisualAssetRenderError("未找到可验证的本地中文字体，不能把可能出现 tofu 的成片标记为 ready")


def layout_display_text(text, style, *, max_width, max_lines=None):
    """A conservative, deterministic CJK layout contract; text is never rewritten."""
    text = str(text)
    if style not in TEXT_STYLES or not text.strip():
        raise VisualAssetRenderError("Display Text 为空或 typography role 无效")
    token = TEXT_STYLES[style]
    limit = token["max_lines"] if max_lines is None else int(max_lines)
    cells = max(1, int(max_width // (token["font_size"] * 1.08)))
    lines = [text[index:index + cells] for index in range(0, len(text), cells)]
    if len(lines) > limit:
        raise VisualAssetRenderError("Display Text 超出安全容量，必须降级而不是缩写、改写或无限缩小")
    return {"text": text, "lines": lines, "font_size": token["font_size"], "font_weight": token["weight"], "line_height": 1.32, "max_width": int(max_width), "max_lines": limit}


def compile_primitives(spec):
    assert_renderable(spec)
    kind = spec["motion_type"]
    elements = spec["elements"]
    primitives = []
    if kind == "svg_path_drawing":
        primitives.append({"kind": "path", "growth": "directional", "d": "M 300 540 L 1620 540"})
        primitives.extend({"kind": "node", "text": x.get("text", ""), "reveal_order": index + 1} for index, x in enumerate(elements))
    elif kind == "causal_chain":
        primitives = [{"kind": "node", "text": x.get("text", ""), "reveal_order": index + 1} for index, x in enumerate(elements)] + [{"kind": "arrow", "reveal_order": index + 2} for index in range(max(0, len(elements) - 1))]
    elif kind == "timeline":
        primitives = [{"kind": "line"}] + [{"kind": "node", "text": x.get("text", ""), "reveal_order": index + 1} for index, x in enumerate(elements)]
    elif kind == "comparison_mechanism":
        primitives = [{"kind": "card", "text": x.get("text", ""), "reveal_order": index + 1} for index, x in enumerate(elements)]
    else:
        primitives = [{"kind": "shape", "text": x.get("text", ""), "reveal_order": index + 1} for index, x in enumerate(elements)] + [{"kind": "transition"}]
    return {"payload_version": "visual-primitives/1", "style": "Neutral Editorial", "motion_type": kind, "primitives": primitives, "duration_seconds": float(spec["source_time_range"]["end_seconds"]) - float(spec["source_time_range"]["start_seconds"])}


def _is_numeric(text):
    return bool(re.fullmatch(r"[+−-]?\d+(?:\.\d+)?(?:\s*[亿万%])?", text.strip()))


def _positioned_text(payload, spec):
    labels = [primitive["text"] for primitive in payload["primitives"] if primitive.get("text")]
    kind = payload["motion_type"]
    entries = [{"role": "title", "layout": layout_display_text(spec["visual_intent"], "title", max_width=1728), "x": 96, "y": 74, "width": 1728, "order": 0}]
    count = max(1, len(labels))
    for index, text in enumerate(labels):
        role = "numeric" if _is_numeric(text) else ("heading" if kind in {"svg_path_drawing", "causal_chain", "controlled_conceptual_metaphor"} else "body")
        if kind == "timeline":
            width, y = min(560, 1728 // count), 625
        elif kind == "comparison_mechanism":
            width, y = 500 if count <= 3 else 360, 390
        elif kind in {"svg_path_drawing", "causal_chain"}:
            width, y = min(440, 1728 // count), 480
        else:
            width, y = min(560, 1728 // count), 470
        center_x = 960 if count == 1 else 96 + width / 2 + index * ((1728 - width) / (count - 1))
        layout = layout_display_text(text, role, max_width=width)
        entries.append({"role": role, "layout": layout, "x": round(center_x - width / 2), "center_x": round(center_x), "y": y, "width": width, "order": index + 1})
    return entries


def _runtime_source():
    return '''import {AbsoluteFill, Composition, Easing, interpolate, useCurrentFrame} from "remotion";
import asset from "./visual-asset.json";
import "./index.css";
const clamp = {extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const};
const P: React.FC<{entry: any}> = ({entry}) => { const f = useCurrentFrame(); const opacity = entry.order === 0 ? 1 : interpolate(f, [entry.order * 8, entry.order * 8 + 10], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)}); return <div data-motion-element="bound-display-text" style={{position:"absolute", left:entry.x, top:entry.y, width:entry.width, color:"#f4f7f6", opacity, fontFamily:asset.font_family + ", sans-serif", fontSize:entry.layout.font_size, fontWeight:entry.layout.font_weight, lineHeight:entry.layout.line_height, overflow:"hidden", wordBreak:"break-all", textAlign:"center"}}>{entry.layout.lines.map((line:string, i:number)=><div key={i}>{line}</div>)}</div>; };
const Shapes: React.FC = () => { const kind = asset.motion_type; return <><div style={{position:"absolute",left:150,right:150,top:548,height:kind === "timeline" || kind === "svg_path_drawing" ? 8 : 0,background:"#58716c"}}/>{asset.entries.slice(1).map((entry:any, i:number)=> <div key={i} data-motion-element={kind} style={{position:"absolute",left:entry.center_x - (kind === "comparison_mechanism" ? entry.width / 2 + 20 : 210),top:kind === "comparison_mechanism" ? 310 : 430,width:kind === "comparison_mechanism" ? entry.width + 40 : 420,height:kind === "comparison_mechanism" ? 270 : 170,border:"4px solid #50d6b5",borderRadius:20,background:"#1b2928"}}/> )}</>; };
const Visual: React.FC = () => <AbsoluteFill style={{backgroundColor:"#101722"}}><Shapes/>{asset.entries.map((entry:any)=><P key={entry.order} entry={entry}/>)}</AbsoluteFill>;
export const RemotionRoot: React.FC = () => <Composition id="VisualAsset" component={Visual} durationInFrames={asset.duration_frames} fps={30} width={1920} height={1080}/>;
'''


def _run(command, *, cwd, error):
    run = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=240)
    if run.returncode:
        detail = (run.stderr or run.stdout)[-1200:]
        raise VisualAssetRenderError(f"{error}: {detail}")


def _write_runtime(project, payload):
    src = project / "src"
    (src / "visual-asset.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (src / "Root.tsx").write_text(_runtime_source(), encoding="utf-8")
    (src / "index.ts").write_text('import {registerRoot} from "remotion"; import {RemotionRoot} from "./Root"; registerRoot(RemotionRoot);\n', encoding="utf-8")
    (src / "index.css").write_text('* { box-sizing: border-box; } html, body { margin: 0; }\n', encoding="utf-8")


def render_visual_asset(spec, output_root, filename):
    try:
        assert_renderable(spec)
    except MotionSpecError as exc:
        raise VisualAssetRenderError(str(exc)) from exc
    payload = compile_primitives(spec)
    entries = _positioned_text(payload, spec)
    if not entries or any(not entry["layout"]["text"].strip() for entry in entries):
        raise VisualAssetRenderError("required Display Text 缺失，不能交付 ready 视频")
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / filename
    template = Path(__file__).resolve().parents[2] / "renderer_templates" / "remotion"
    node_modules = template / "node_modules"
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not node_modules.is_dir() or not chrome.is_file():
        raise VisualAssetRenderError("本地 Remotion/Chrome runtime 不完整，不能退回无文字 ffmpeg 成片")
    runtime_payload = {"motion_type": payload["motion_type"], "entries": entries, "font_family": _font_family(), "duration_frames": max(30, math.ceil(payload["duration_seconds"] * CANVAS["fps"]))}
    with tempfile.TemporaryDirectory(prefix="deeptalk-visual-remotion-") as raw:
        project = Path(raw) / "project"
        shutil.copytree(template, project, ignore=shutil.ignore_patterns("node_modules", "production-plan.json", "production-profile.json", "asset-map.json", "ProductionComposition.tsx"))
        (project / "node_modules").symlink_to(node_modules)
        _write_runtime(project, runtime_payload)
        common = ["npx", "remotion"]
        _run(common + ["render", "src/index.ts", "VisualAsset", str(output), "--codec=h264", "--concurrency=1", "--log=error", f"--browser-executable={chrome}"], cwd=project, error="中文 Display Text Render 失败")
        reference = output.with_suffix(".text-reference.png")
        _run(common + ["still", "src/index.ts", "VisualAsset", str(reference), "--frame=45", "--log=error", f"--browser-executable={chrome}"], cwd=project, error="中文 Display Text reference frame 失败")
    if not output.is_file() or output.stat().st_size <= 1000 or not reference.is_file() or reference.stat().st_size <= 1000:
        raise VisualAssetRenderError("required Display Text 未得到有效 MP4/reference frame，不能标记 ready")
    evidence = {"evidence_version": "visual-display-text/1", "renderer": "remotion-browser", "font_family": runtime_payload["font_family"], "visible_text": [entry["layout"]["text"] for entry in entries], "reference_frame": str(reference), "layout_status": "bounded", "source_time_range": dict(spec["source_time_range"]), "spec_digest": spec["spec_digest"]}
    output.with_suffix(".text-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
