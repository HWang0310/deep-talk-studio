"""Primary human-editable production delivery: Asset Pack + Edit Map.

This module deliberately packages independently QA-ready assets.  It never
touches Clean A-roll media, does not create a full edited video, and does not
write an NLE project.  All row clocks are copied from the accepted semantic
timeline produced from the real A-roll alignment.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class AssetPackWorkflowError(ValueError):
    """The formal creator-facing package cannot be safely assembled."""


DECISIONS = {"KEEP_A_ROLL", "REAL_MATERIAL", "MG_MOTION", "ADVANCED_MOTION"}
FALLBACKS = {
    "ADVANCED_MOTION": ("MG_MOTION", "REAL_MATERIAL", "KEEP_A_ROLL"),
    "MG_MOTION": ("REAL_MATERIAL", "KEEP_A_ROLL"),
    "REAL_MATERIAL": ("KEEP_A_ROLL",),
    "KEEP_A_ROLL": (),
}
ASSET_DIRECTORIES = {
    "REAL_MATERIAL": "06_真实素材",
    "MG_MOTION": "07_MG动画",
    "ADVANCED_MOTION": "08_高级动画",
}


@dataclass(frozen=True)
class ProductionAssetPackResult:
    delivery_mode: str
    manifest: Mapping
    machine_map: Mapping
    markdown_path: Path
    csv_path: Path
    json_path: Path
    manifest_path: Path
    requires_human_review: bool


def _digest(value: Mapping) -> str:
    data = dict(value)
    data.pop("map_digest", None)
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _timecode(value: str) -> str:
    milliseconds = round(float(value) * 1000)
    seconds, ms = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"


def _validate_roots(roots: Mapping) -> None:
    if roots.get("clean_aroll_gate_status") != "accepted" or roots.get("timing_provenance") != "actual_aroll_alignment":
        raise AssetPackWorkflowError("没有通过 Clean A-roll Alignment，不能生成正式 Edit Map")
    for key in ("alignment_digest", "transcript_digest"):
        if len(str(roots.get(key, ""))) != 64:
            raise AssetPackWorkflowError("正式 Edit Map 缺少真实 A-roll lineage")


def _safe_asset(asset: Mapping, decision: str) -> bool:
    path = Path(str(asset.get("local_path", "")))
    if asset.get("asset_class") != decision or asset.get("qa_status") != "ready" or not path.is_file():
        return False
    expected = str(asset.get("sha256", ""))
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    return len(expected) == 64 and expected == actual and bool(str(asset.get("filename", "")).strip())


def _asset_for(opportunity_id: str, decision: str, assets: Sequence[Mapping]) -> Mapping | None:
    for asset in assets:
        if asset.get("opportunity_id") == opportunity_id and _safe_asset(asset, decision):
            return asset
    return None


def _place_asset(episode_root: Path, asset: Mapping) -> Path:
    source = Path(str(asset["local_path"])).resolve()
    destination = episode_root / ASSET_DIRECTORIES[asset["asset_class"]] / str(asset["filename"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != asset["sha256"]:
            raise AssetPackWorkflowError("同名素材已存在且内容不同，不能覆盖用户文件")
        return destination
    shutil.copy2(source, destination)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != asset["sha256"]:
        raise AssetPackWorkflowError("素材复制后 SHA 不一致")
    return destination


def _row(span: Mapping, opportunity: Mapping, asset: Mapping | None, fallback_outcome: str) -> dict:
    decision = opportunity["decision"] if asset is not None or opportunity["decision"] == "KEEP_A_ROLL" else fallback_outcome
    start = str(span["actual_start_seconds"]); end = str(span["actual_end_seconds"])
    if decision == "KEEP_A_ROLL":
        placement = "保持人物画面。"
        filename = ""
        provenance = ""
        qa_status = "not_applicable"
    else:
        placement = str(asset.get("placement_advice") or "按时间放入对应位置，结束后回到人物。")
        filename = str(asset["filename"])
        provenance = str(asset.get("provenance", ""))
        qa_status = "pass"
    return {
        "sequence": 0,
        "span_id": str(span["span_id"]),
        "actual_start_seconds": start,
        "actual_end_seconds": end,
        "actual_start_timecode": _timecode(start),
        "actual_end_timecode": _timecode(end),
        "spoken_summary": str(span["summary"]),
        "decision": decision,
        "asset_filename": filename,
        "placement_advice": placement,
        "why": str(opportunity.get("why_visual", "保留人物表达。")),
        "provenance": provenance,
        "qa_status": qa_status,
        "fallback_outcome": fallback_outcome,
        "alignment_digest": str(opportunity.get("alignment_digest", "")),
    }


def _choose_asset(opportunity: Mapping, assets: Sequence[Mapping]) -> tuple[str, Mapping | None]:
    decision = str(opportunity.get("decision", "KEEP_A_ROLL"))
    if decision not in DECISIONS:
        raise AssetPackWorkflowError("Visual Director decision 无效")
    candidate = _asset_for(str(opportunity["opportunity_id"]), decision, assets)
    if decision == "KEEP_A_ROLL":
        return "KEEP_A_ROLL", None
    if candidate:
        return decision, candidate
    for fallback in FALLBACKS[decision]:
        candidate = _asset_for(str(opportunity["opportunity_id"]), fallback, assets)
        if candidate:
            return fallback, candidate
    return "KEEP_A_ROLL", None


def _markdown(rows: Sequence[Mapping]) -> str:
    blocks = ["# 剪辑表", "", "按下面的真实口播时间，在剪映把素材拖到对应位置。没有素材的段落保持人物画面。"]
    for row in rows:
        blocks.extend([
            "",
            f"## {row['actual_start_timecode']}–{row['actual_end_timecode']}",
            f"内容：{row['spoken_summary']}",
            f"建议：{row['decision']}",
            f"素材：{row['asset_filename'] or '不需要素材，保持人物。'}",
            f"怎么放：{row['placement_advice']}",
            f"原因：{row['why']}",
        ])
        if row["provenance"]:
            blocks.append(f"来源：{row['provenance']}")
        blocks.append(f"QA：{row['qa_status']}")
    return "\n".join(blocks) + "\n"


def _csv(rows: Sequence[Mapping]) -> str:
    fields = [
        "sequence", "actual_start_seconds", "actual_end_seconds", "actual_start_timecode", "actual_end_timecode",
        "spoken_summary", "decision", "asset_filename", "placement_advice", "why", "provenance", "qa_status", "fallback_outcome",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows({key: row[key] for key in fields} for row in rows)
    return stream.getvalue()


def build_production_asset_pack(
    accepted_roots: Mapping,
    semantic_timeline: Sequence[Mapping],
    visual_director_plan: Mapping,
    asset_candidates: Sequence[Mapping],
    *,
    episode_root: Path,
    created_at: str,
) -> ProductionAssetPackResult:
    """Assemble only independently usable assets and an exact human edit guide."""
    _validate_roots(accepted_roots)
    if visual_director_plan.get("alignment_digest") != accepted_roots["alignment_digest"]:
        raise AssetPackWorkflowError("Visual Director 与真实 A-roll Alignment 不一致")
    spans = {str(item.get("span_id", "")): item for item in semantic_timeline}
    if not spans or any(not item.get("actual_start_seconds") or not item.get("actual_end_seconds") for item in spans.values()):
        raise AssetPackWorkflowError("Semantic Timeline 缺少真实 A-roll 时间")
    opportunities = list(visual_director_plan.get("opportunities", []))
    if {str(item.get("span_id", "")) for item in opportunities} != set(spans):
        raise AssetPackWorkflowError("Visual Director 必须覆盖每个真实语义 span")
    root = Path(episode_root).resolve()
    directories = [root / name for name in ("05_A-roll", "06_真实素材", "07_MG动画", "08_高级动画", "09_剪辑表", "_DeepTalk记录")]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    rows = []
    manifest_assets = []
    needs_advanced_review = False
    for opportunity in opportunities:
        span = spans[str(opportunity["span_id"])]
        intended = str(opportunity.get("decision", "KEEP_A_ROLL"))
        if intended == "ADVANCED_MOTION" and opportunity.get("review_requirement") != "advanced_spec_review":
            raise AssetPackWorkflowError("Advanced Motion 必须进入单独 Review")
        if intended == "ADVANCED_MOTION":
            needs_advanced_review = True
        actual_decision, asset = _choose_asset(opportunity, asset_candidates)
        effective = dict(opportunity); effective["decision"] = actual_decision
        if asset is not None:
            placed = _place_asset(root, asset)
            record = dict(asset)
            record.update(local_path=str(placed), time_range={"start_seconds": str(span["actual_start_seconds"]), "end_seconds": str(span["actual_end_seconds"])})
            manifest_assets.append(record)
        row = _row(span, effective, asset, actual_decision)
        row["sequence"] = len(rows) + 1
        rows.append(row)
    rows.sort(key=lambda item: (float(item["actual_start_seconds"]), item["sequence"]))
    for index, row in enumerate(rows, 1):
        row["sequence"] = index
    manifest = {
        "artifact_version": "visual-asset-manifest/1",
        "asset_count": len(manifest_assets),
        "assets": manifest_assets,
        "alignment_digest": accepted_roots["alignment_digest"],
        "transcript_digest": accepted_roots["transcript_digest"],
    }
    manifest["manifest_digest"] = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    machine_map = {
        "artifact_version": "edit-map/1",
        "created_at": str(created_at),
        "delivery_mode": "asset_pack",
        "timing_provenance": "actual_aroll_alignment",
        "alignment_digest": accepted_roots["alignment_digest"],
        "transcript_digest": accepted_roots["transcript_digest"],
        "asset_manifest_digest": manifest["manifest_digest"],
        "rows": rows,
    }
    machine_map["map_digest"] = _digest(machine_map)
    edit_dir = root / "09_剪辑表"; record_dir = root / "_DeepTalk记录"
    markdown_path = edit_dir / "剪辑表.md"; csv_path = edit_dir / "剪辑表.csv"; json_path = record_dir / "edit-map.json"; manifest_path = record_dir / "visual-asset-manifest.json"
    markdown_path.write_text(_markdown(rows), encoding="utf-8")
    csv_path.write_text(_csv(rows), encoding="utf-8-sig")
    json_path.write_text(json.dumps(machine_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ProductionAssetPackResult("asset_pack", manifest, machine_map, markdown_path, csv_path, json_path, manifest_path, needs_advanced_review)
