"""Human-readable Material Package view; JSON remains the machine interface."""

from .models import MaterialPackage


def render_material_markdown(package: MaterialPackage) -> str:
    ready = sum(item["eligibility_status"] == "ready_to_use" for item in package.materials)
    references = sum(item["eligibility_status"] == "reference_only" for item in package.materials)
    generated = sum(item["eligibility_status"] == "ready_to_use" for item in package.generated_visuals)
    lines = [
        "# 本期素材与画面准备单", "",
        f"状态：{package.status}",
        f"共 {len(package.cue_sheet)} 个画面提示；可直接使用 {ready} 项；仅供参考 {references} 项；原创画面 {generated} 项。",
        "", "## 画面提示", "",
    ]
    role_names = {"evidence": "证据", "context": "背景", "illustration": "说明", "transition": "转场"}
    for cue in package.cue_sheet:
        lines.append(
            f"- 在“{cue['placement_anchor']}”处：{cue['reason']}（{role_names[cue['visual_role']]}，约 {cue['suggested_duration_seconds']} 秒）"
        )
    lines.extend(["", "## 推荐素材", ""])
    status_names = {
        "ready_to_use": "可直接使用", "reference_only": "仅作引用参考",
        "permission_required": "使用前需取得许可", "rejected": "不要使用",
    }
    for item in package.materials:
        lines.append(
            f"- {item['title']}：{status_names[item['eligibility_status']]}。{item['suggested_usage']}"
        )
    if package.generated_visuals:
        lines.extend(["", "## 原创画面", ""])
        for visual in package.generated_visuals:
            lines.append(f"- {visual['title']}：{visual['visual_type']}，约 {visual['suggested_duration_seconds']} 秒。")
    if package.gaps:
        lines.extend(["", "## 仍缺少", ""] + [f"- {gap}" for gap in package.gaps])
    if package.research_update_required["required"]:
        lines.extend(["", "## 需要先更新研究", "", "搜索中发现可能影响现有稿件的新信息，已停止自动改稿和制图。"])
    if package.warnings:
        lines.extend(["", "## 使用提醒", ""] + [f"- {warning}" for warning in package.warnings])
    return "\n".join(lines).rstrip() + "\n"

