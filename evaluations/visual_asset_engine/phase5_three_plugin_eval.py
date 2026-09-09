"""Reproducible Phase 5 evaluation for the three pinned real Contract V1 runners.

Generated media and machine artifacts are written to a caller-selected output
directory.  Nothing in this module enables the tracked production config.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from deeptalk_studio.candidate_edit_map import (
    build_edit_map_csv,
    build_edit_map_json,
    build_edit_map_markdown,
    write_candidate_edit_map,
)
from deeptalk_studio.candidate_pack_workflow import (
    build_candidate_asset_pack,
    save_candidate_asset_pack,
)
from deeptalk_studio.candidate_portfolio import orchestrate_candidate_portfolio
from deeptalk_studio.candidate_portfolio_storage import save_candidate_portfolio
from deeptalk_studio.visual_generation_policy import load_candidate_generation_policy


CORE_ROOT = Path(__file__).resolve().parents[2]
DEEPTALK_ROOT = CORE_ROOT.parents[1] if CORE_ROOT.parent.name == ".worktrees" else CORE_ROOT.parent
TASK_ID = "DT-CORE-5-001"
PLAN_DIGEST = hashlib.sha256(b"DT-CORE-5-001 sanitized synthetic corpus v1").hexdigest()
PLUGIN_IDS = (
    "org.deeptalk.mg",
    "org.deeptalk.illustrated-metaphor",
    "org.deeptalk.handdrawn-animation",
)
EXPECTED_FAMILIES = {"MG", "Illustrated Metaphor", "HANDDRAWN_SVG"}

SYNTHETIC_CORPUS = (
    {
        "opportunity_id": "VO-DT-CORE-5-001-structural",
        "spoken_semantics": "持续累积的资源占用通过因果传导机制，使分散压力逐步集中并最终越过临界点。",
        "visual_purpose": "用结构化隐喻和分阶段因果过程解释积累、压力与临界变化。",
        "a_roll_window": {"start_ms": 12000, "end_ms": 20000},
        "target_duration_ms": 7000,
        "language": "zh-CN",
        "canvas": {"width": 1920, "height": 1080},
        "semantic_context": "虚构的资源系统用于验证生成式视觉候选，不代表真实事件或实体。",
        "factual_context": [],
    },
    {
        "opportunity_id": "VO-DT-CORE-5-001-numeric",
        "spoken_semantics": "虚构样本留存率由 42% 变为 58%。",
        "visual_purpose": "仅呈现两个精确百分比，供观众直接读取。",
        "a_roll_window": {"start_ms": 24000, "end_ms": 30000},
        "target_duration_ms": 5000,
        "language": "zh-CN",
        "canvas": {"width": 1920, "height": 1080},
        "semantic_context": "这些百分比是合成测试值。",
        "factual_context": [],
    },
)


def real_plugin_config(plugin_roots: Mapping[str, Path]) -> dict:
    config = json.loads(
        (CORE_ROOT / "config/visual-asset-plugins.example.json").read_text(encoding="utf-8")
    )
    config = copy.deepcopy(config)
    if set(plugin_roots) != set(PLUGIN_IDS):
        raise ValueError("plugin_roots must contain the three pinned Phase 5 plugin IDs")
    for plugin in config["plugins"]:
        plugin["enabled"] = True
        plugin["plugin_root"] = str(Path(plugin_roots[plugin["plugin_id"]]).resolve())
    return config


def _semantic_snapshot(portfolio: Mapping[str, Any]) -> dict:
    """Order-proof projection retaining raw and Core lineage, not wall-clock data."""
    opportunities = []
    for block in portfolio["opportunities"]:
        opportunities.append({
            "opportunity": block["opportunity"],
            "proposals": [
                {
                    "plugin_id": item["plugin_id"],
                    "resolved_plugin_version": item["resolved_plugin_version"],
                    "suitability_raw": item["suitability_raw"],
                }
                for item in block["proposals"]
            ],
            "policy_records": block["policy_records"],
            "generation_records": [
                {"plugin_id": item["plugin_id"], "generation_raw": item["generation_raw"]}
                for item in block["generation_records"]
            ],
            "candidates": block["candidates"],
        })
    audit_lineage = [
        {
            "opportunity_id": item["opportunity_id"],
            "plugin_id": item["plugin_id"],
            "operation": item["operation"],
            "task_id": item["execution"]["task_id"],
            "resolved_plugin_version": item["execution"]["resolved_plugin_version"],
            "config_digest": item["execution"]["config_digest"],
            "environment_digest": item["execution"]["environment_digest"],
            "configured_runner": item["execution"]["configured_runner"],
            "configured_version_command": item["execution"]["configured_version_command"],
            "request_identity": item["execution"]["request_identity"],
            "result_identity": item["execution"]["result_identity"],
            "preflight": item["execution"]["preflight"],
            "job_locator": item["execution"]["job_locator"],
            "request_locator": item["execution"]["request_locator"],
            "result_locator": item["execution"]["result_locator"],
            "output_locator": item["execution"]["output_locator"],
            "status": item["execution"]["status"],
            "retryable": item["execution"]["retryable"],
            "reason": item["execution"]["reason"],
            "raw_response": item["raw_response"],
            "request_snapshot": item["request_snapshot"],
        }
        for item in portfolio["audit_records"]
    ]
    return {
        "portfolio_id": portfolio["portfolio_id"],
        "visual_opportunity_plan_digest": portfolio["visual_opportunity_plan_digest"],
        "plugin_config_digest": portfolio["plugin_config_digest"],
        "generation_policy_digest": portfolio["generation_policy_digest"],
        "production_profile": portfolio["production_profile"],
        "opportunities": opportunities,
        "audit_lineage": audit_lineage,
    }


def _run_portfolio(
    config: Mapping[str, Any],
    *,
    job_root: Path,
    invocation_order: Sequence[str],
    collection_order: Sequence[str],
    namespace: str,
) -> dict:
    return orchestrate_candidate_portfolio(
        SYNTHETIC_CORPUS,
        config,
        production_profile="RICH",
        policy=load_candidate_generation_policy(
            CORE_ROOT / "config/candidate-generation-profile.json"
        ),
        job_root=job_root,
        visual_opportunity_plan_digest=PLAN_DIGEST,
        task_id=TASK_ID,
        request_namespace=namespace,
        plugin_invocation_order=invocation_order,
        plugin_collection_order=collection_order,
    )


def _probe_media(path: Path, *, expected_duration_ms: int) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height:format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    evidence = json.loads(result.stdout)
    streams = evidence.get("streams")
    stream = streams[0] if isinstance(streams, list) and streams else {}
    try:
        duration_ms = float(evidence.get("format", {}).get("duration", 0)) * 1000
    except (TypeError, ValueError):
        duration_ms = 0
    if (
        stream.get("codec_name") != "h264"
        or stream.get("width") != 1920
        or stream.get("height") != 1080
        or duration_ms <= 0
        or abs(duration_ms - expected_duration_ms) > 100
    ):
        raise RuntimeError(f"PRIMARY_MEDIA is not a readable non-empty video: {path}")
    return evidence


def _write_json(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_phase5_evaluation(output_root: Path, plugin_roots: Mapping[str, Path]) -> dict:
    output_root = Path(output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError("Phase 5 evaluation output root must be absent or empty")
    output_root.mkdir(parents=True, exist_ok=True)
    config = real_plugin_config(plugin_roots)

    forward = _run_portfolio(
        config,
        job_root=output_root / "success-forward" / "jobs",
        invocation_order=PLUGIN_IDS,
        collection_order=tuple(reversed(PLUGIN_IDS)),
        namespace="DT-CORE-5-001-success",
    )
    reverse = _run_portfolio(
        config,
        job_root=output_root / "success-reverse" / "jobs",
        invocation_order=tuple(reversed(PLUGIN_IDS)),
        collection_order=PLUGIN_IDS,
        namespace="DT-CORE-5-001-success",
    )
    if _semantic_snapshot(forward) != _semantic_snapshot(reverse):
        raise RuntimeError("runner invocation/collection order changed canonical semantics")

    forward_portfolio_path = save_candidate_portfolio(
        forward, output_root / "success-forward" / "artifacts"
    )
    reverse_portfolio_path = save_candidate_portfolio(
        reverse, output_root / "success-reverse" / "artifacts"
    )
    pack = build_candidate_asset_pack(
        forward,
        job_root=output_root / "success-forward" / "jobs",
        dest_root=output_root / "success-forward" / "creator-pack" / "media",
    )
    pack_path = save_candidate_asset_pack(
        pack, output_root / "success-forward" / "creator-pack"
    )
    edit_map = build_edit_map_json(pack)
    map_paths = write_candidate_edit_map(
        edit_map,
        build_edit_map_csv(pack),
        build_edit_map_markdown(pack),
        output_root / "success-forward" / "creator-pack" / "edit-map",
    )

    structural = forward["opportunities"][0]
    accepted = [
        item for item in structural["candidates"]
        if item["plugin_candidate"].get("candidate_status") == "READY"
        and item["core_acceptance"].get("status") == "ACCEPTED"
    ]
    families = {item["plugin_candidate"]["asset_family"] for item in accepted}
    if len(accepted) != 3 or families != EXPECTED_FAMILIES:
        raise RuntimeError(f"expected three distinct READY/ACCEPTED families, got {families}")
    numeric = forward["opportunities"][1]
    numeric_policy = {item["plugin_id"]: item for item in numeric["policy_records"]}
    numeric_proposals = {item["plugin_id"]: item for item in numeric["proposals"]}

    def is_complete_abstain(plugin_id: str) -> bool:
        policy_record = numeric_policy.get(plugin_id, {})
        proposal_record = numeric_proposals.get(plugin_id, {})
        execution = proposal_record.get("suitability_execution") or {}
        raw = proposal_record.get("suitability_raw") or {}
        return (
            policy_record.get("generation_call") == "NOT_REQUESTED"
            and policy_record.get("no_call_reason") == "ABSTAIN"
            and execution.get("status") == "COMPLETED"
            and raw.get("operation_status") == "COMPLETED"
            and raw.get("suitability") == "ABSTAIN"
        )

    numeric_abstains = {
        plugin_id for plugin_id in PLUGIN_IDS if is_complete_abstain(plugin_id)
    }
    if numeric_abstains != set(PLUGIN_IDS) or numeric["candidates"]:
        raise RuntimeError("numeric synthetic opportunity must naturally produce three ABSTAIN outcomes")

    probes = {}
    for opportunity in pack["opportunities"]:
        for candidate in opportunity["candidates"]:
            media_path = Path(candidate["primary_media"]["staged_path"])
            probes[candidate["candidate_id"]] = _probe_media(
                media_path, expected_duration_ms=int(candidate["duration_ms"]),
            )

    failure_config = copy.deepcopy(config)
    for plugin in failure_config["plugins"]:
        if plugin["plugin_id"] == "org.deeptalk.illustrated-metaphor":
            plugin["expected_source_revision"] = "0" * 40
    failure = _run_portfolio(
        failure_config,
        job_root=output_root / "failure-isolation" / "jobs",
        invocation_order=tuple(reversed(PLUGIN_IDS)),
        collection_order=PLUGIN_IDS,
        namespace="DT-CORE-5-001-failure",
    )
    failure_portfolio_path = save_candidate_portfolio(
        failure, output_root / "failure-isolation" / "artifacts"
    )
    failure_pack = build_candidate_asset_pack(
        failure,
        job_root=output_root / "failure-isolation" / "jobs",
        dest_root=output_root / "failure-isolation" / "creator-pack" / "media",
    )
    failure_pack_path = save_candidate_asset_pack(
        failure_pack, output_root / "failure-isolation" / "creator-pack"
    )
    failure_map = build_edit_map_json(failure_pack)
    failure_map_paths = write_candidate_edit_map(
        failure_map,
        build_edit_map_csv(failure_pack),
        build_edit_map_markdown(failure_pack),
        output_root / "failure-isolation" / "creator-pack" / "edit-map",
    )
    failure_structural = failure["opportunities"][0]
    failed_proposal = next(
        item for item in failure_structural["proposals"]
        if item["plugin_id"] == "org.deeptalk.illustrated-metaphor"
    )
    failure_candidates = [
        item for item in failure_structural["candidates"]
        if item["core_acceptance"].get("status") == "ACCEPTED"
    ]
    if (
        failed_proposal["suitability_execution"]["status"] != "FAILED"
        or failed_proposal["suitability_raw"] is not None
        or len(failure_candidates) != 2
        or len(failure_pack["opportunities"][0]["candidates"]) != 2
        or len(failure_map["opportunities"][0]["candidates"]) != 2
    ):
        raise RuntimeError("one-plugin preflight failure was not isolated from successful candidates")

    evidence = {
        "task_id": TASK_ID,
        "synthetic_only": True,
        "production_enabled": False,
        "contract_version": "visual-asset-plugin-contract/1",
        "order_independence": "PASS",
        "failure_isolation": "PASS",
        "product_technical_validation": "PASS",
        "portfolio_id": forward["portfolio_id"],
        "candidate_ids": [item["plugin_candidate"]["candidate_id"] for item in accepted],
        "asset_families": sorted(families),
        "numeric_no_call_plugins": sorted(numeric_abstains),
        "numeric_abstain_plugins": sorted(numeric_abstains),
        "creator_eligible_candidate_ids": [
            item["plugin_candidate"]["candidate_id"] for item in accepted
        ],
        "failure_plugin": "org.deeptalk.illustrated-metaphor",
        "failure_surviving_candidate_ids": [
            item["plugin_candidate"]["candidate_id"] for item in failure_candidates
        ],
        "media_probes": probes,
        "artifacts": {
            "forward_portfolio": str(forward_portfolio_path),
            "reverse_portfolio": str(reverse_portfolio_path),
            "candidate_pack": str(pack_path),
            "candidate_edit_map_json": str(map_paths["json_path"]),
            "candidate_edit_map_csv": str(map_paths["csv_path"]),
            "candidate_edit_map_markdown": str(map_paths["markdown_path"]),
            "failure_portfolio": str(failure_portfolio_path),
            "failure_candidate_pack": str(failure_pack_path),
            "failure_candidate_edit_map_json": str(failure_map_paths["json_path"]),
        },
    }
    _write_json(output_root / "phase5-evidence.json", evidence)
    return evidence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--mg-root", type=Path,
        default=DEEPTALK_ROOT / "deeptalk-mg",
    )
    parser.add_argument(
        "--illustrated-root", type=Path,
        default=DEEPTALK_ROOT / "deeptalk-illustrated-metaphor",
    )
    parser.add_argument(
        "--handdrawn-root", type=Path,
        default=DEEPTALK_ROOT / "deeptalk-handdrawn-animation",
    )
    args = parser.parse_args(argv)
    evidence = run_phase5_evaluation(
        args.output_root,
        {
            "org.deeptalk.mg": args.mg_root,
            "org.deeptalk.illustrated-metaphor": args.illustrated_root,
            "org.deeptalk.handdrawn-animation": args.handdrawn_root,
        },
    )
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
