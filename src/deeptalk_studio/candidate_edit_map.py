"""Candidate Edit Map: creator-facing JSON, CSV, and Markdown from a Candidate Asset Pack.

This module is strictly additive to V1.  It reads a ``candidate-asset-pack/1``
artifact and produces three parallel creator-facing outputs:

* **JSON** — opportunity-centred, same structure as the pack but with only
  creator-relevant fields (no plugin-internal metadata).
* **CSV** — flat rows, one candidate per row; same ``opportunity_id`` may
  appear multiple times.
* **Markdown** — opportunity-grouped, human-readable; clearly tells the
  creator they may choose none, one, or several candidates.

Key design rules (Phase 4 acceptance):

* ``suggested_review_order`` is exposed only as "查看顺序" (review order).
  No winner / best / recommended language.
* No plugin-internal metadata, runner argv, process logs, or opaque debug
  fields in any output.
* Overlapping candidate time windows are presented without resolution —
  the creator decides.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


class CandidateEditMapError(ValueError):
    """The candidate edit map cannot be safely generated."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def build_edit_map_json(pack: Mapping[str, Any]) -> dict:
    """Build ``candidate-edit-map/1`` JSON from a candidate asset pack.

    The JSON is opportunity-centred: each opportunity object contains an
    array of candidate entries.  Only creator-relevant fields are included;
    plugin-internal metadata is stripped.
    """
    if pack.get("artifact_version") != "candidate-asset-pack/1":
        raise CandidateEditMapError("只接受 candidate-asset-pack/1")

    opportunities_out: list[dict[str, Any]] = []
    for opp in pack.get("opportunities", []):
        candidates_out: list[dict[str, Any]] = []
        for c in opp.get("candidates", []):
            entry: dict[str, Any] = {
                "candidate_id": str(c.get("candidate_id", "")),
                "asset_family": str(c.get("asset_family", "")),
                "duration_ms": int(c.get("duration_ms", 0)),
                "duration_timecode": str(c.get("duration_timecode", "")),
                "suggested_placement": c.get("suggested_placement", {}),
                "a_roll_window": c.get("a_roll_window", {}),
                "qa_summary": c.get("qa_summary", {}),
                "provenance": c.get("provenance", {}),
                "primary_media": {
                    "filename": str(c.get("primary_media", {}).get("filename", "")),
                    "locator": str(c.get("primary_media", {}).get("locator", "")),
                },
                "review_order": int(c.get("review_order", 0)),
            }
            if c.get("preview_media") and c["preview_media"].get("locator"):
                entry["preview_media"] = {
                    "locator": str(c["preview_media"]["locator"]),
                }
            candidates_out.append(entry)

        opportunities_out.append({
            "opportunity_id": str(opp.get("opportunity_id", "")),
            "a_roll_window": opp.get("a_roll_window", {}),
            "visual_purpose": str(opp.get("visual_purpose", "")),
            "semantic_context": str(opp.get("semantic_context", "")),
            "candidates": candidates_out,
        })

    result: dict[str, Any] = {
        "artifact_version": "candidate-edit-map/1",
        "source_pack_digest": str(pack.get("pack_digest", "")),
        "opportunities": opportunities_out,
    }
    result["map_digest"] = _digest(result)
    return result


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "opportunity_id",
    "a_roll_start_timecode",
    "a_roll_end_timecode",
    "visual_purpose",
    "candidate_id",
    "asset_family",
    "duration_ms",
    "duration_timecode",
    "placement_start_timecode",
    "placement_end_timecode",
    "primary_media_filename",
    "primary_media_locator",
    "preview_media_locator",
    "qa_status",
    "qa_summary",
    "provenance_origin",
    "review_order",
]


def build_edit_map_csv(pack: Mapping[str, Any]) -> str:
    """Build a CSV string: one candidate per row.

    The same ``opportunity_id`` may appear in multiple rows when an
    opportunity has multiple candidates.  Overlapping placements are
    presented without resolution.
    """
    if pack.get("artifact_version") != "candidate-asset-pack/1":
        raise CandidateEditMapError("只接受 candidate-asset-pack/1")

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
    writer.writeheader()

    for opp in pack.get("opportunities", []):
        opp_id = str(opp.get("opportunity_id", ""))
        window = opp.get("a_roll_window", {})
        start_tc = str(window.get("start_timecode", ""))
        end_tc = str(window.get("end_timecode", ""))
        purpose = str(opp.get("visual_purpose", ""))

        for c in opp.get("candidates", []):
            placement = c.get("suggested_placement", {})
            primary = c.get("primary_media", {}) or {}
            preview = c.get("preview_media") or {}
            qa = c.get("qa_summary", {})
            prov = c.get("provenance", {})
            row = {
                "opportunity_id": opp_id,
                "a_roll_start_timecode": start_tc,
                "a_roll_end_timecode": end_tc,
                "visual_purpose": purpose,
                "candidate_id": str(c.get("candidate_id", "")),
                "asset_family": str(c.get("asset_family", "")),
                "duration_ms": int(c.get("duration_ms", 0)),
                "duration_timecode": str(c.get("duration_timecode", "")),
                "placement_start_timecode": str(placement.get("start_timecode", "")),
                "placement_end_timecode": str(placement.get("end_timecode", "")),
                "primary_media_filename": str(primary.get("filename", "")),
                "primary_media_locator": str(primary.get("locator", "")),
                "preview_media_locator": str(preview.get("locator", "")),
                "qa_status": str(qa.get("status", "")),
                "qa_summary": str(qa.get("summary", "")),
                "provenance_origin": str(prov.get("origin", "")),
                "review_order": int(c.get("review_order", 0)),
            }
            writer.writerow(row)

    return stream.getvalue()


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def build_edit_map_markdown(pack: Mapping[str, Any]) -> str:
    """Build opportunity-grouped Markdown for creators.

    Clearly tells the creator: you may choose none, one, or several
    candidates.  No winner / best / recommended language.  Plugin-internal
    metadata is absent.
    """
    if pack.get("artifact_version") != "candidate-asset-pack/1":
        raise CandidateEditMapError("只接受 candidate-asset-pack/1")

    lines: list[str] = [
        "# 候选素材表",
        "",
        "以下候选素材按 Visual Opportunity 分组。每个 Opportunity 下可能有零个、一个或多个候选。",
    "你可以不用、用一个或同时用多个候选——候选之间互不排他，时间窗口重叠时由你决定如何处理。",
    "系统不会替你选择，也不会自动剪辑。",
        "",
    ]

    total_candidates = sum(
        len(opp.get("candidates", []))
        for opp in pack.get("opportunities", [])
    )

    if total_candidates == 0:
        lines.append("本次没有可用的候选素材。")
        return "\n".join(lines) + "\n"

    for opp in pack.get("opportunities", []):
        window = opp.get("a_roll_window", {})
        lines.extend([
            "",
            f"## Opportunity：{opp.get('opportunity_id', '')}",
            "",
            f"- A-roll 时间窗口：{window.get('start_timecode', '')} – {window.get('end_timecode', '')}",
            f"- 视觉目的：{opp.get('visual_purpose', '')}",
        ])
        context = opp.get("semantic_context", "")
        if context:
            lines.append(f"- 语义上下文：{context}")

        candidates = opp.get("candidates", [])
        if not candidates:
            lines.extend(["", "本次该 Opportunity 没有可用候选。"])
            continue

        lines.append("")
        for c in candidates:
            placement = c.get("suggested_placement", {})
            primary = c.get("primary_media", {}) or {}
            qa = c.get("qa_summary", {})
            prov = c.get("provenance", {})
            lines.extend([
                f"### {c.get('candidate_id', '')}",
                "",
                f"- 素材家族：{c.get('asset_family', '')}",
                f"- 时长：{c.get('duration_timecode', '')}（{c.get('duration_ms', 0)} ms）",
                f"- 建议放置位置：{placement.get('start_timecode', '')} – {placement.get('end_timecode', '')}",
                f"- 素材文件：{primary.get('filename', '')}",
                f"- 查看顺序：第 {c.get('review_order', 0)} 个",
            ])
            preview = c.get("preview_media")
            if preview and preview.get("locator"):
                lines.append(f"- 预览：{preview['locator']}")
            if qa.get("summary"):
                lines.append(f"- QA：{qa.get('status', '')} — {qa['summary']}")
            else:
                lines.append(f"- QA：{qa.get('status', '')}")
            if prov.get("origin"):
                lines.append(f"- 来源：{prov['origin']}")
                if prov.get("source_ref"):
                    lines.append(f"  - 来源引用：{prov['source_ref']}")

    lines.extend(["", "---", "", "以上候选素材仅供参考使用。你可以不用、用一个或用多个。"])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Write all outputs
# ---------------------------------------------------------------------------

def write_candidate_edit_map(
    edit_map_json: Mapping[str, Any],
    csv_text: str,
    markdown_text: str,
    dest_dir: Path,
) -> dict[str, Path]:
    """Write JSON, CSV, and Markdown files to *dest_dir*.

    Returns a dict with ``json_path``, ``csv_path``, and ``markdown_path``.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    json_path = dest_dir / "candidate-edit-map.json"
    csv_path = dest_dir / "candidate-edit-map.csv"
    markdown_path = dest_dir / "candidate-edit-map.md"

    json_path.write_text(
        json.dumps(edit_map_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    csv_path.write_text(csv_text, encoding="utf-8-sig")
    markdown_path.write_text(markdown_text, encoding="utf-8")

    return {
        "json_path": json_path,
        "csv_path": csv_path,
        "markdown_path": markdown_path,
    }
