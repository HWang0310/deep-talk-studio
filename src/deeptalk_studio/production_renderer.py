"""Plain-Chinese reading view for a completed or planned production run."""

from typing import Any, Mapping


def render_production_summary(
    plan: Mapping[str, Any], *, ready_count: int, failed_count: int
) -> str:
    lines = [
        "这期视频素材已经生成：",
        "",
        f"动画素材：{len(plan.get('motion_assets', []))} 个",
        f"可直接使用：{ready_count} 个",
        f"需要人工补：{len(plan.get('production_gaps', [])) + failed_count} 个",
        "",
        "粗剪视觉预览：" + ("已生成" if ready_count else "尚未生成"),
    ]
    gaps = plan.get("production_gaps", [])
    if gaps:
        lines.extend(["", "仍需注意："])
        for gap in gaps:
            lines.append(f'- {gap["reason"]} 建议：{gap["recommended_fallback"]}')
    return "\n".join(lines) + "\n"
