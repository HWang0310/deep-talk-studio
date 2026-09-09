"""Render five safe synthetic assets; never a real episode or product acceptance."""
import hashlib
import json
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
        ("时间线.mp4", _opportunity(1, "MG_MOTION"), {"motion_type": "timeline", "visual_intent": "事件时间线", "elements": [{"kind": "node", "text": "8 月 24 日", "origin": "editorial"}, {"kind": "node", "text": "首周口碑", "origin": "editorial"}]}),
        ("因果链.mp4", _opportunity(2, "MG_MOTION"), {"motion_type": "causal_chain", "visual_intent": "因果链", "elements": [{"kind": "node", "text": "社交讨论", "origin": "editorial"}, {"kind": "node", "text": "二次传播", "origin": "editorial"}]}),
        ("机制对照.mp4", _opportunity(3, "MG_MOTION"), {"motion_type": "comparison_mechanism", "visual_intent": "机制对照", "elements": [{"kind": "card", "text": "3.2 亿", "origin": "editorial"}, {"kind": "card", "text": "+47%", "origin": "editorial"}, {"kind": "card", "text": "B站 / AI", "origin": "editorial"}]}),
        ("路线生长.mp4", _opportunity(4, "ADVANCED_MOTION"), {"motion_type": "svg_path_drawing", "visual_intent": "路径建立", "why_advanced_not_mg": "路径就是叙事", "elements": [{"kind": "node", "text": "起点：讨论", "origin": "editorial"}, {"kind": "node", "text": "终点：传播", "origin": "editorial"}]}),
        ("概念转换.mp4", _opportunity(5, "ADVANCED_MOTION"), {"motion_type": "controlled_conceptual_metaphor", "visual_intent": "概念转换", "why_advanced_not_mg": "需要物理转换动作", "elements": [{"kind": "shape", "text": "电影票", "origin": "editorial"}, {"kind": "shape", "text": "参与资格", "origin": "editorial"}]}),
    ]
    assets = []
    for index, (filename, opportunity, content) in enumerate(specs, 1):
        spec = build_motion_spec(opportunity, content, spec_id=f"MS{index:03d}")
        if opportunity["decision"] == "ADVANCED_MOTION": spec = approve_advanced_motion_spec(spec, "fixture review approved")
        folder = root / ("07_MG动画" if opportunity["decision"] == "MG_MOTION" else "08_高级动画")
        path = render_visual_asset(spec, folder, filename); _probe(path)
        evidence = json.loads(path.with_suffix(".text-evidence.json").read_text(encoding="utf-8"))
        if not set(element["text"] for element in content["elements"]).issubset(evidence["visible_text"]):
            raise RuntimeError("fixture asset 未证明 bound 中文 Display Text 已进入 browser render")
        assets.append({"filename": filename, "local_path": str(path), "qa_status": "ready", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "duration_seconds": "2", "time_range": opportunity["source_time_range"], "purpose": content["visual_intent"], "why": "工程 fixture：验证确定性视觉素材链路", "fallback": "如果觉得太花，保留真人。", "spec_digest": spec["spec_digest"]})
    manifest = build_manifest(assets); pack = write_asset_pack(root, manifest); build_edit_map(manifest, pack["edit_dir"])
    stress_content = {"motion_type": "causal_chain", "visual_intent": "为什么票房还在上涨？ +47% · 8 月 24 日", "elements": [{"kind": "node", "text": "首周口碑", "origin": "editorial"}, {"kind": "node", "text": "社交讨论", "origin": "editorial"}, {"kind": "node", "text": "二次传播", "origin": "editorial"}, {"kind": "node", "text": "3.2 亿", "origin": "editorial"}, {"kind": "node", "text": "B站 / AI", "origin": "editorial"}]}
    stress_spec = build_motion_spec(_opportunity(99, "MG_MOTION"), stress_content, spec_id="MS-STRESS")
    stress_path = render_visual_asset(stress_spec, root / "_DeepTalk记录", "中文压力测试.mp4")
    _probe(stress_path)
    stress_evidence = json.loads(stress_path.with_suffix(".text-evidence.json").read_text(encoding="utf-8"))
    if any(sample not in "\n".join(stress_evidence["visible_text"]) for sample in ("为什么票房还在上涨？", "首周口碑", "社交讨论", "二次传播", "3.2 亿", "+47%", "8 月 24 日", "B站 / AI")):
        raise RuntimeError("中文压力 fixture 缺少 required Display Text")
    return {"manifest": manifest, "root": root, "chinese_stress_path": stress_path, "chinese_stress_evidence": stress_evidence}
