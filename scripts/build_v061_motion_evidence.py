#!/usr/bin/env python3
"""Build copyright-free V0.6.1 three-bar motion evidence with both renderers."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from deeptalk_studio.production_planner import production_plan_digest
from deeptalk_studio.production_profile import load_production_profile
from deeptalk_studio.production_qa import build_motion_asset_manifest, prepare_production_qa
from deeptalk_studio.production_renderers import get_renderer
from deeptalk_studio.production_renderers.base import RendererCheckResult
from deeptalk_studio.production_schema import PRODUCTION_PLAN_SCHEMA
from deeptalk_studio.validation import validate_json_schema


CREATED_AT = "2026-08-11T18:00:00+08:00"


def display(text, *, machine=False):
    return {
        "text": text,
        "origin": "machine_editorial" if machine else "visual_label",
        "text_kind": "editorial" if machine else "factual",
        "claim_ids": [] if machine else ["C-SYNTHETIC"],
        "evidence_link_ids": [] if machine else ["E-SYNTHETIC"],
    }


def synthetic_plan(profile):
    points = [
        ("第一阶段", 36, "36 单位"),
        ("第二阶段", 64, "64 单位"),
        ("第三阶段", 88, "88 单位"),
    ]
    scene = {
        "scene_id": "S001", "cue_id": "VC001", "beat_id": "B001",
        "placement_anchor": "这是一组完全虚构的公开动效测试数据。",
        "visual_role": "illustration", "source_material_ids": [],
        "source_visual_ids": [], "scene_type": "bar_motion",
        "duration_seconds": 3.0, "duration_frames": 90,
        "renderer_intent": "三根柱从共同基线依次增长，数值和标签随后出现",
        "transition_intent": "editorial_push",
        "layout_intent": "三柱独立、顺序稳定、最终状态完整可读",
        "scene_payload": {
            "payload_version": "0.6.1", "payload_type": "bar",
            "timeline_events": [],
            "bar_data_points": [
                {"order": index, "label": display(label), "value": value,
                 "value_label": display(value_label)}
                for index, (label, value, value_label) in enumerate(points, 1)
            ],
            "comparison_items": [], "diagram_nodes": [], "diagram_edges": [],
            "image_asset_id": "", "capture_region": "",
        },
        "on_screen_text": [display("数据对比", machine=True)],
        "audio_mode": "none", "warnings": [],
    }
    plan = {
        "artifact_version": "0.6.1", "production_id": "PROD-v061-synthetic-motion",
        "revision": 1, "previous_revision": 0, "created_at": CREATED_AT,
        "generated_at": CREATED_AT, "script_id": "SCR-SYNTHETIC", "script_revision": 1,
        "script_content_digest": "a" * 64, "material_package_id": "MAT-SYNTHETIC",
        "material_package_revision": 1, "material_package_digest": "b" * 64,
        "material_review_id": "MRV-SYNTHETIC",
        "production_profile_version": profile["profile_version"],
        "renderer_mode": "remotion", "selected_renderer": "remotion",
        "canvas": dict(profile["canvas"]), "scenes": [scene],
        "motion_assets": [
            {"motion_asset_id": "MA001", "scene_id": "S001", "asset_kind": "motion_clip", "requested_format": "mp4"},
            {"motion_asset_id": "MAPREVIEW", "scene_id": "S001", "asset_kind": "rough_preview", "requested_format": "mp4"},
            {"motion_asset_id": "HERO001", "scene_id": "S001", "asset_kind": "hero_still", "requested_format": "png"},
        ],
        "production_gaps": [], "warnings": [], "qa_state": {"state": "not_run"},
    }
    plan["plan_digest"] = production_plan_digest(plan)
    validate_json_schema(plan, PRODUCTION_PLAN_SCHEMA, "synthetic_plan")
    return plan


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing evidence directory: {output}")
    output.mkdir(parents=True)
    profile = load_production_profile()
    plan = synthetic_plan(profile)
    (output / "synthetic-production-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    package = SimpleNamespace(materials=[], generated_visuals=[])
    evidence = {"version": "0.6.1", "fictional_data": True, "renderers": {}}
    for offset, renderer_name in enumerate(("remotion", "hyperframes"), 1):
        renderer_plan = json.loads(json.dumps(plan))
        renderer_plan["renderer_mode"] = renderer_name
        renderer_plan["selected_renderer"] = renderer_name
        renderer_plan["plan_digest"] = production_plan_digest(renderer_plan)
        renderer = get_renderer(renderer_name)
        prepared = renderer.prepare_project(
            renderer_plan, package, profile, output / "no-material-assets",
            output / "projects",
        )
        checks = list(renderer.validate_project(prepared))
        preview = renderer.preview(prepared, port=3260 + offset)
        checks.append(preview)
        if any(check.outcome != "pass" for check in checks):
            raise RuntimeError(f"{renderer_name} validation/preview failed: {checks}")
        batch = renderer.render(prepared, renderer_plan, output / "rendered" / renderer_name)
        manifest = build_motion_asset_manifest(
            renderer_plan, renderer_name, batch, created_at=CREATED_AT,
            manifest_id=f"MAM-v061-{renderer_name}",
        )
        qa = prepare_production_qa(
            renderer_plan, manifest, created_at=CREATED_AT,
            qa_id=f"PQA-v061-{renderer_name}",
            renderer_checks=[RendererCheckResult(
                "environment", "core", 0, "pass", "environment", "环境可用。",
            ), *checks],
        )
        if qa["package_gate_status"] != "pass":
            raise RuntimeError(f"{renderer_name} QA did not pass")
        clip = next(
            Path(asset["output_path"]) for asset in manifest.manifest["assets"]
            if asset["motion_asset_id"] == "MA001"
        )
        public_clip = output / f"synthetic-three-bar-{renderer_name}.mp4"
        shutil.copyfile(clip, public_clip)
        (output / f"manifest-{renderer_name}.json").write_text(
            json.dumps(manifest.manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (output / f"qa-{renderer_name}.json").write_text(
            json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(public_clip)],
            capture_output=True, text=True, check=True,
        )
        evidence["renderers"][renderer_name] = {
            "clip": public_clip.name, "sha256": sha256(public_clip),
            "byte_size": public_clip.stat().st_size,
            "ffprobe": json.loads(probe.stdout),
            "qa_gate": qa["package_gate_status"],
            "checks": [check.to_dict() for check in checks],
        }
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(output / "synthetic-three-bar-remotion.mp4"),
         "-vf", "fps=1,tile=3x1", "-frames:v", "1", str(output / "synthetic-three-bar-contact-sheet.png")],
        check=True,
    )
    evidence["contact_sheet"] = {
        "file": "synthetic-three-bar-contact-sheet.png",
        "sha256": sha256(output / "synthetic-three-bar-contact-sheet.png"),
    }
    (output / "evidence-summary.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
