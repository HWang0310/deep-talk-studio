"""Deterministic final-MP4 evidence for aligned visual placements."""
import hashlib
import json
import subprocess
from pathlib import Path


class OutputTruthError(ValueError):
    pass


def _frame(video: Path, seconds: float, destination: Path) -> str:
    result = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video), "-frames:v", "1", str(destination)], capture_output=True, text=True)
    if result.returncode or not destination.is_file() or not destination.stat().st_size:
        raise OutputTruthError("无法从最终 Preview 提取验证帧")
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def _presentation_mode(placement: dict) -> str:
    layout = placement.get("layout_mode", "")
    if layout in {"", "full_screen_broll", "full_screen_visual"}:
        return "primary_visual"
    if layout == "picture_in_picture":
        return "primary_visual_with_pip"
    return "supporting_overlay"


def build_output_truth_evidence(preview_path: Path, placements, *, evidence_dir: Path, sample_limit: int = 5) -> dict:
    """Sample pre/in/post final encoded frames; fail closed for invisible primary spans."""
    ready = [p for p in placements if p.get("placement_status") == "ready" and p.get("source_kind") != "clean_aroll"][:sample_limit]
    if not ready:
        raise OutputTruthError("没有可验证的 ready visual placement")
    root = Path(evidence_dir)
    root.mkdir(parents=True, exist_ok=False)
    rows = []
    for p in ready:
        start = int(p["preview_in_frame"]) / 30
        end = int(p["preview_out_frame"]) / 30
        if end <= start:
            raise OutputTruthError("Visual placement 没有有效 Preview window")
        times = (max(0, start - 0.5), (start + end) / 2, end + 0.5)
        labels = ("pre", "in", "post")
        files = [root / f"{p['placement_id']}-{label}.png" for label in labels]
        hashes = [_frame(Path(preview_path), value, destination) for value, destination in zip(times, files)]
        if len(set(hashes)) < 2:
            raise OutputTruthError("最终 Preview 未显示 placement 的可见画面变化")
        rows.append({"placement_id": p["placement_id"], "source_kind": p["source_kind"], "expected_presentation_mode": _presentation_mode(p), "timestamps_seconds": [round(x, 3) for x in times], "frame_sha256": hashes, "frame_files": [file.name for file in files], "final_mux_source": str(preview_path)})
    data = {"artifact_version": "output-truth-evidence/1", "preview_sha256": hashlib.sha256(Path(preview_path).read_bytes()).hexdigest(), "placements": rows}
    data["evidence_digest"] = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return data


def validate_output_truth_evidence(evidence: dict, preview_path: Path) -> None:
    value = dict(evidence); digest = value.pop("evidence_digest", "")
    if digest != hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest() or value.get("preview_sha256") != hashlib.sha256(Path(preview_path).read_bytes()).hexdigest():
        raise OutputTruthError("Output-Truth evidence 与最终 Preview 不一致")
    if not value.get("placements") or any(len(set(row.get("frame_sha256", []))) < 2 or len(row.get("frame_files", [])) != 3 for row in value["placements"]):
        raise OutputTruthError("Output-Truth evidence 不足")
