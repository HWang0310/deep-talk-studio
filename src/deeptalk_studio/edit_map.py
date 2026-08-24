"""Derived creator-facing Markdown/CSV Edit Map without machine internals."""
import csv
import io
from pathlib import Path


def _tc(seconds):
    value = int(float(seconds)); return f"{value // 60:02d}:{value % 60:02d}"


def build_edit_map(manifest, output_dir):
    rows = []
    for asset in manifest.get("assets", []):
        if asset.get("qa_status") != "ready": continue
        time = asset["time_range"]; rows.append({"时间": f"{_tc(time['start_seconds'])}–{_tc(time['end_seconds'])}", "素材": asset["filename"], "建议": f"全屏约 {asset['duration_seconds']} 秒", "用途": asset["purpose"], "为什么": asset["why"], "备选": asset["fallback"]})
    markdown = "# 剪辑表\n\n" + "\n\n".join("\n".join([row["时间"], f"素材：{row['素材']}", f"建议：{row['建议']}", f"用途：{row['用途']}", f"为什么：{row['为什么']}", f"备选：{row['备选']}"]) for row in rows) + "\n"
    stream = io.StringIO(); writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["时间", "素材", "建议", "用途", "为什么", "备选"]); writer.writeheader(); writer.writerows(rows)
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "剪辑表.md").write_text(markdown, encoding="utf-8")
    (output_dir / "剪辑表.csv").write_text(stream.getvalue(), encoding="utf-8")
    return {"artifact_version": "edit-map/1", "markdown": markdown, "csv_text": stream.getvalue(), "rows": rows}
