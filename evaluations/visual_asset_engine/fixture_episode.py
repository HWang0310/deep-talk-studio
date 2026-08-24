"""Render five safe synthetic assets; never a real episode or product acceptance."""
import hashlib
import subprocess
from pathlib import Path

from deeptalk_studio.edit_map import build_edit_map
from deeptalk_studio.motion_spec import approve_advanced_motion_spec, build_motion_spec
from deeptalk_studio.visual_asset_pack import build_manifest, write_asset_pack
from deeptalk_studio.visual_asset_renderer import render_visual_asset


def _opportunity(index, decision):
    return {"opportunity_id": f"VO{index:03d}", "decision": decision, "source_time_range": {"start_seconds": str((index - 1) * 8), "end_seconds": str(index * 8)}, "alignment_digest": "a" * 64}


def _probe(path):
    run = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,r_frame_rate", "-of", "default=noprint_wrappers=1", str(path)], capture_output=True, text=True, check=False)
    if run.returncode or "width=1920" not in run.stdout or "height=1080" not in run.stdout:
        raise RuntimeError("fixture asset 未通过 ffprobe")


def run_fixture_episode(root):
    root = Path(root); specs = [
        ("时间线.mp4", _opportunity(1, "MG_MOTION"), {"motion_type": "timeline", "visual_intent": "事件顺序", "elements": [{"kind": "node", "text": "起点", "origin": "editorial"}, {"kind": "node", "text": "结果", "origin": "editorial"}]}),
        ("因果链.mp4", _opportunity(2, "MG_MOTION"), {"motion_type": "causal_chain", "visual_intent": "因果", "elements": [{"kind": "node", "text": "原因", "origin": "editorial"}, {"kind": "node", "text": "结果", "origin": "editorial"}]}),
        ("机制对照.mp4", _opportunity(3, "MG_MOTION"), {"motion_type": "comparison_mechanism", "visual_intent": "机制对照", "elements": [{"kind": "card", "text": "机制一", "origin": "editorial"}, {"kind": "card", "text": "机制二", "origin": "editorial"}]}),
        ("路线生长.mp4", _opportunity(4, "ADVANCED_MOTION"), {"motion_type": "svg_path_drawing", "visual_intent": "路径建立", "why_advanced_not_mg": "路径就是叙事", "elements": [{"kind": "node", "text": "开始", "origin": "editorial"}, {"kind": "node", "text": "到达", "origin": "editorial"}]}),
        ("概念转换.mp4", _opportunity(5, "ADVANCED_MOTION"), {"motion_type": "controlled_conceptual_metaphor", "visual_intent": "抽象概念转换", "why_advanced_not_mg": "需要物理转换动作", "elements": [{"kind": "shape", "text": "电影票", "origin": "editorial"}, {"kind": "shape", "text": "参与资格", "origin": "editorial"}]}),
    ]
    assets = []
    for index, (filename, opportunity, content) in enumerate(specs, 1):
        spec = build_motion_spec(opportunity, content, spec_id=f"MS{index:03d}")
        if opportunity["decision"] == "ADVANCED_MOTION": spec = approve_advanced_motion_spec(spec, "fixture review approved")
        folder = root / ("07_MG动画" if opportunity["decision"] == "MG_MOTION" else "08_高级动画")
        path = render_visual_asset(spec, folder, filename); _probe(path)
        assets.append({"filename": filename, "local_path": str(path), "qa_status": "ready", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "duration_seconds": "2", "time_range": opportunity["source_time_range"], "purpose": content["visual_intent"], "why": "工程 fixture：验证确定性视觉素材链路", "fallback": "如果觉得太花，保留真人。", "spec_digest": spec["spec_digest"]})
    manifest = build_manifest(assets); pack = write_asset_pack(root, manifest); build_edit_map(manifest, pack["edit_dir"])
    return {"manifest": manifest, "root": root}
