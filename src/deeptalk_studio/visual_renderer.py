"""Deterministic, dependency-free 16:9 SVG renderer for approved Visual Specs."""

import hashlib
import html
from pathlib import Path
from typing import Mapping


class VisualRenderError(RuntimeError):
    pass


def _t(value: object) -> str:
    return html.escape(str(value), quote=True)


def _header(spec: Mapping[str, object]) -> str:
    return (
        f'<text x="96" y="110" class="title">{_t(spec["title"])}</text>'
        f'<text x="96" y="160" class="subtitle">{_t(spec["subtitle"])}</text>'
    )


def _timeline(spec: Mapping[str, object]) -> str:
    events = spec["events"]
    count = len(events)
    start, end, y = 160, 1760, 540
    parts = [f'<line x1="{start}" y1="{y}" x2="{end}" y2="{y}" class="line"/>']
    for index, event in enumerate(events):
        x = start if count == 1 else start + (end - start) * index / (count - 1)
        parts.extend([
            f'<circle cx="{x:.0f}" cy="{y}" r="18" class="accent"/>',
            f'<text x="{x:.0f}" y="{y-70}" text-anchor="middle" class="date">{_t(event["date"])}</text>',
            f'<text x="{x:.0f}" y="{y+80}" text-anchor="middle" class="body">{_t(event["label"])}</text>',
        ])
    return "".join(parts)


def _bar(spec: Mapping[str, object]) -> str:
    points = spec["data_points"]
    maximum = max(float(point["value"]) for point in points) or 1
    parts = []
    for index, point in enumerate(points):
        y = 300 + index * min(140, 600 / max(1, len(points)))
        width = 1050 * float(point["value"]) / maximum
        parts.extend([
            f'<text x="120" y="{y+34:.0f}" class="body">{_t(point["label"])}</text>',
            f'<rect x="500" y="{y}" width="{width:.0f}" height="56" rx="12" class="accent"/>',
            f'<text x="{520+width:.0f}" y="{y+38:.0f}" class="value">{_t(point["value_label"])}</text>',
        ])
    return "".join(parts)


def _comparison(spec: Mapping[str, object]) -> str:
    parts = []
    for index, item in enumerate(spec["comparison_items"]):
        y = 310 + index * 190
        parts.extend([
            f'<text x="960" y="{y-35}" text-anchor="middle" class="date">{_t(item["label"])}</text>',
            f'<rect x="110" y="{y}" width="790" height="120" rx="18" class="panel"/>',
            f'<rect x="1020" y="{y}" width="790" height="120" rx="18" class="panel"/>',
            f'<text x="505" y="{y+70}" text-anchor="middle" class="body">{_t(item["left_text"])}</text>',
            f'<text x="1415" y="{y+70}" text-anchor="middle" class="body">{_t(item["right_text"])}</text>',
        ])
    return "".join(parts)


def _diagram(spec: Mapping[str, object]) -> str:
    nodes = spec["nodes"]
    positions = {}
    parts = []
    for index, node in enumerate(nodes):
        x = 250 + index * (1420 / max(1, len(nodes) - 1)) if len(nodes) > 1 else 960
        positions[node["node_id"]] = (x, 540)
    for edge in spec["edges"]:
        x1, y1 = positions[edge["from_node"]]
        x2, y2 = positions[edge["to_node"]]
        parts.extend([
            f'<line x1="{x1:.0f}" y1="{y1}" x2="{x2:.0f}" y2="{y2}" class="line"/>',
            f'<text x="{(x1+x2)/2:.0f}" y="{y1-35}" text-anchor="middle" class="small">{_t(edge["label"])}</text>',
        ])
    for node in nodes:
        x, y = positions[node["node_id"]]
        parts.extend([
            f'<rect x="{x-150:.0f}" y="{y-65}" width="300" height="130" rx="24" class="panel accent-stroke"/>',
            f'<text x="{x:.0f}" y="{y+12}" text-anchor="middle" class="body">{_t(node["label"])}</text>',
        ])
    return "".join(parts)


def render_visual_svg(spec: Mapping[str, object], output_root: Path) -> Path:
    visual_type = spec.get("visual_type")
    renderer = {"timeline": _timeline, "bar": _bar, "comparison": _comparison, "diagram": _diagram}.get(visual_type)
    if renderer is None:
        raise VisualRenderError(f"不支持的 Visual 类型：{visual_type}")
    if spec.get("width") != 1920 or spec.get("height") != 1080:
        raise VisualRenderError("V0.5 SVG 必须使用 1920×1080")
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (root / f'{spec["visual_id"]}.svg').resolve()
    if target.parent != root or target.exists():
        raise VisualRenderError("Visual 目标越界或已经存在，拒绝覆盖")
    body = renderer(spec)
    attribution = _t(spec["attribution"])
    metadata = _t("claim_ids=" + ",".join(spec["claim_ids"]) + "; evidence_link_ids=" + ",".join(spec["evidence_link_ids"]))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080" role="img" aria-label="{_t(spec['title'])}">
<metadata>{metadata}</metadata>
<style>
.bg{{fill:#101216}} .title{{fill:#f7f8fa;font:700 58px sans-serif}} .subtitle{{fill:#aeb6c2;font:30px sans-serif}}
.body{{fill:#f7f8fa;font:34px sans-serif}} .date{{fill:#f0b65a;font:700 30px sans-serif}} .small{{fill:#aeb6c2;font:24px sans-serif}}
.value{{fill:#f7f8fa;font:700 30px sans-serif}} .line{{stroke:#77808d;stroke-width:8}} .accent{{fill:#f0b65a}}
.panel{{fill:#20242b}} .accent-stroke{{stroke:#f0b65a;stroke-width:5}}
</style>
<rect width="1920" height="1080" class="bg"/>{_header(spec)}{body}
<text x="96" y="1010" class="small">来源：{attribution}</text>
</svg>
'''
    target.write_text(svg, encoding="utf-8")
    return target


def visual_asset_record(path: Path) -> dict:
    data = Path(path).read_bytes()
    return {"local_path": str(Path(path).resolve()), "byte_size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "mime_type": "image/svg+xml"}

