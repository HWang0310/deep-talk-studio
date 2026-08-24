"""Deterministic SVG-frame renderer shared by MVP visual asset grammars."""
import subprocess
from pathlib import Path

from .motion_spec import MotionSpecError, assert_renderable


class VisualAssetRenderError(ValueError):
    pass


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


def render_visual_asset(spec, output_root, filename):
    try: assert_renderable(spec)
    except MotionSpecError as exc: raise VisualAssetRenderError(str(exc)) from exc
    payload = compile_primitives(spec); output_root = Path(output_root); output_root.mkdir(parents=True, exist_ok=True); output = output_root / filename
    # ffmpeg on the supported local runtime has no SVG decoder.  Keep SVG-like
    # primitives as the shared semantic contract and render their neutral
    # editorial fallback directly with deterministic ffmpeg draw primitives.
    labels = [p.get("text", "") for p in payload["primitives"] if p.get("text")]
    filters = ["drawbox=x=300:y=535:w='1320*min(1,t/2)':h=10:color=0x50d6b5:t=fill"]
    for index, label in enumerate(labels[:5]):
        x = 300 + index * (1320 // max(1, len(labels) - 1))
        filters += [f"drawbox=x={x-28}:y=512:w=56:h=56:color=0x50d6b5:t=fill:enable='gte(t,{index*0.32})'"]
    run = subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x101722:s=1920x1080:r=30:d=2", "-vf", ",".join(filters), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)], capture_output=True, text=True, timeout=120)
    if run.returncode != 0 or not output.is_file() or output.stat().st_size <= 1000:
        raise VisualAssetRenderError("本地 SVG Motion Renderer 未能生成有效 MP4")
    return output
