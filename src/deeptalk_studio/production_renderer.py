"""Plain-Chinese reading view for a completed or planned production run."""

from typing import Any, Mapping


def render_production_summary(
    plan: Mapping[str, Any], *, ready_count: int, failed_count: int,
    preview_ready: bool = False, motion_clip_ready_count: int = 0,
) -> str:
    lines = [
        "这期视频素材已经生成：",
        "",
        f"动画素材：{len(plan.get('motion_assets', []))} 个",
        f"可直接使用：{ready_count} 个",
        f"需要人工补：{len(plan.get('production_gaps', [])) + failed_count} 个",
        "",
    ]
    if preview_ready:
        lines.append("粗剪视觉预览：已生成")
    else:
        lines.append(
            f"粗剪视觉预览生成失败，但已有 {motion_clip_ready_count} 个独立 Motion Clip 可用。"
        )
    gaps = plan.get("production_gaps", [])
    if gaps:
        lines.extend(["", "仍需注意："])
        for gap in gaps:
            lines.append(f'- {gap["reason"]} 建议：{gap["recommended_fallback"]}')
    return "\n".join(lines) + "\n"
