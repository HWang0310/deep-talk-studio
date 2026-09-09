"""Reproducible no-key large-v3 evidence and full production-session runner.

This module deliberately writes only into the user-level DeepTalk cache.  It
does not modify Selection Gate history, nor does it change provider timing:
raw token overlaps are reported and remain a blocking condition.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

# Direct ``python path/to/script.py`` is the documented production command.
# Python otherwise puts only this nested folder on sys.path, not the repo root.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from deeptalk_studio.edit_bridge_session import (
    resolve_real_edit_bridge_session,
    run_real_edit_bridge_session,
)
from deeptalk_studio.narration_media import canonical_digest, sha256_file
from deeptalk_studio.transcription.local_asr_selection import parse_whisper_cpp_json
from deeptalk_studio.transcription.local_whisper_cpp import (
    LocalWhisperCppTranscriptionProvider,
    WhisperCppTokenOverlapError,
)

from evaluations.local_asr_selection.run_selection_gate import _audio_info, _one_chunk_plan, _timed_chain


API_KEY_NAMES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY")
OVERLAP_REQUIRED_FIELDS = frozenset(
    {
        "chunk_id",
        "chunk_index",
        "previous_segment_index",
        "current_segment_index",
        "same_segment",
        "previous_raw_token_index",
        "current_raw_token_index",
        "previous_provider_order",
        "current_provider_order",
        "previous_token_text",
        "current_token_text",
        "previous_raw_start_seconds",
        "previous_raw_end_seconds",
        "current_raw_start_seconds",
        "current_raw_end_seconds",
        "overlap_duration_seconds",
        "previous_is_control_token",
        "current_is_control_token",
        "is_chunk_boundary",
        "model",
        "dtw_preset",
        "runtime_version",
        "raw_response_digest",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _api_key_evidence() -> Dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in API_KEY_NAMES}


def _term_presence(text: str, terms: Iterable[str]) -> Dict[str, bool]:
    return {term: term in text for term in terms}


def build_overlap_report(
    overlaps: Sequence[Mapping[str, Any]], *, audio_sha256: str, provider_metadata: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """Return complete immutable raw overlap evidence or reject incomplete data."""

    copied = []
    for item in overlaps:
        missing = OVERLAP_REQUIRED_FIELDS.difference(item)
        if missing:
            raise ValueError("overlap evidence is incomplete: " + ", ".join(sorted(missing)))
        copied.append(dict(item))
    report: Dict[str, Any] = {
        "artifact_version": "local-whisper-large-v3-overlap-evidence/1",
        "created_at": _now(),
        "audio_sha256": audio_sha256,
        "overlap_count": len(copied),
        "overlaps": copied,
        "canonicalization": "not_attempted; raw provider timing remains fail-closed",
    }
    if provider_metadata is not None:
        report["provider"] = dict(provider_metadata)
    report["artifact_digest"] = canonical_digest(report)
    return report


def monitor_snapshot(
    *, pid: int, elapsed_seconds: float, alive: bool, output_bytes: int, stage: str
) -> Dict[str, Any]:
    """Represent liveness, never infer a hang merely from elapsed time."""

    return {
        "observed_at": _now(),
        "pid": pid,
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "alive": bool(alive),
        "output_bytes": int(output_bytes),
        "stage": stage,
        "state": "running" if alive else "finished",
    }


def _historical_medium_summary(reference: Path) -> Dict[str, Any]:
    """Read the immutable historical medium output only for light comparison."""

    json_path = reference.parent / "whisper_medium_dtw.json"
    if not json_path.is_file():
        return {"available": False}
    parsed = parse_whisper_cpp_json(json_path, model_version="1.9.2+306c88f4d1286aec1bf96e544632897886af5501")
    text = "".join(unit.spoken_text for unit in parsed.units)
    terms = ("OpenAI", "DeepSeek", "AI Agent", "昇腾", "GPU")
    return {
        "available": True,
        "raw_json_sha256": sha256_file(json_path),
        "token_count": len(parsed.units),
        "proper_noun_exact_presence": _term_presence(text, terms),
        "known_observed_error_examples": [
            "OpenAI → OpenEye",
            "DeepSeek → DeepSeq",
            "AI Agent → AI Agit",
            "昇腾 → 生酮",
            "GPU → GTU",
        ],
    }


def run_large_v3_smoke(audio_path: Path, reference_path: Path, evidence_path: Path) -> Dict[str, Any]:
    """Run one 272-second formal provider pass and persist transparent evidence."""

    audio = Path(audio_path).resolve()
    reference = Path(reference_path).resolve()
    info = _audio_info(audio)
    plan = _one_chunk_plan(audio, info)
    extracted = {
        "artifact_digest": plan.extracted_audio_digest,
        "duration_seconds": info["duration_seconds"],
        "sample_count": info["sample_count"],
        "sample_rate": info["sample_rate"],
    }
    provider = LocalWhisperCppTranscriptionProvider()
    api_keys = _api_key_evidence()
    try:
        provider_result = provider.transcribe(extracted, plan, "zh", "large-v3")
    except WhisperCppTokenOverlapError as exc:
        metadata = {
            "provider": "whisper.cpp",
            "model": "large-v3",
            "dtw_preset": "large.v3",
            "runtime_version": "1.9.2",
            "raw_response_digests": list(exc.raw_response_digests),
        }
        overlap = build_overlap_report(exc.overlaps, audio_sha256=info["sha256"], provider_metadata=metadata)
        overlap_path = evidence_path.parent / "large-v3-overlap-evidence.json"
        _write_json(overlap_path, overlap)
        report = {
            "artifact_version": "local-whisper-large-v3-smoke/1",
            "created_at": _now(),
            "gate_status": "BLOCKED",
            "blocker": "raw whisper.cpp token overlap; no canonicalization was applied",
            "api_keys": api_keys,
            "audio": info,
            "overlap_count": overlap["overlap_count"],
            "overlap_evidence_path": str(overlap_path),
            "overlap_evidence_digest": overlap["artifact_digest"],
        }
        report["artifact_digest"] = canonical_digest(report)
        _write_json(evidence_path, report)
        return report

    transcript_text = "".join(unit.spoken_text for unit in provider_result.units)
    terms = ("OpenAI", "DeepSeek", "AI Agent", "昇腾", "GPU")
    chain = _timed_chain(provider_result, audio, info)
    raw = dict(provider_result.raw_metadata)
    report = {
        "artifact_version": "local-whisper-large-v3-smoke/1",
        "created_at": _now(),
        "gate_status": "PASS",
        "api_keys": api_keys,
        "audio": info,
        "reference": {"sha256": sha256_file(reference), "filename": reference.name},
        "provider": {
            "provider": provider_result.provider,
            "model": provider_result.provider_model,
            "model_version": provider_result.provider_model_version,
            "model_sha256": raw.get("model_sha256"),
            "model_bytes": raw.get("model_bytes"),
            "dtw_preset": raw.get("inference_parameters", {}).get("dtw"),
            "runtime_seconds": raw.get("runtime_seconds"),
            "rtf": raw.get("rtf"),
            "acceleration": raw.get("acceleration"),
            "timestamp_granularity": provider_result.timestamp_granularity,
            "token_count": len(provider_result.units),
            "raw_response_digest": provider_result.raw_response_digest,
            "raw_response_digests": raw.get("response_digests", []),
            "cache_path": raw.get("cache_path"),
            "bootstrap_status": raw.get("bootstrap_status"),
            "runtime_source_commit": raw.get("runtime_source_commit"),
        },
        "transcription_text": transcript_text,
        "proper_noun_exact_presence": _term_presence(transcript_text, terms),
        "obvious_proper_noun_errors": "not manually corrected; inspect raw transcription_text",
        "overlap_count": 0,
        "historical_medium_light_comparison": _historical_medium_summary(reference),
        "timed_transcript_and_alignment": chain,
    }
    report["artifact_digest"] = canonical_digest(report)
    _write_json(evidence_path, report)
    return report


def _output_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _id_factory(kind: str) -> str:
    return f"LV3-{kind}-{uuid.uuid4().hex[:12]}"


def _run_session_child(session_root: Path, repo_root: Path, result_path: Path) -> int:
    """Execute the canonical owner once; the parent is responsible for monitoring."""

    started = time.monotonic()
    try:
        inputs = resolve_real_edit_bridge_session(session_root, repo_root)
        result = run_real_edit_bridge_session(inputs, LocalWhisperCppTranscriptionProvider(), clock=_now, id_factory=_id_factory)
        payload = {
            "status": "PASS",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "preview_path": str(result.preview_path),
            "preview_sha256": sha256_file(result.preview_path),
            "preview_bytes": result.preview_path.stat().st_size,
            "qa": result.qa,
            "paths": {key: str(value) for key, value in result.paths.items()},
            "provider": result.artifacts["transcript"].get("provider"),
            "transcript_digest": result.artifacts["transcript"].get("transcript_digest"),
            "alignment_digest": result.artifacts["alignment"].get("artifact_digest"),
            "subtitle_digest": result.artifacts["subtitle"].get("artifact_digest"),
            "bridge_digest": result.artifacts["bridge"].get("package_digest"),
        }
    except Exception as exc:  # child must leave actionable evidence for a real failure
        payload = {
            "status": "FAILED",
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    _write_json(result_path, payload)
    return 0 if payload["status"] == "PASS" else 1


def run_full_large_v3_session(
    session_root: Path,
    repo_root: Path,
    monitor_path: Path,
    *,
    source_video: Optional[Path] = None,
    poll_interval: float = 15.0,
) -> Dict[str, Any]:
    """Run the real canonical session while recording process/output liveness.

    There is intentionally no elapsed-time kill switch.  A nonzero child exit
    is recorded with its own stage error; a live renderer remains live.
    """

    session = Path(session_root).resolve()
    root = Path(repo_root).resolve()
    monitor = Path(monitor_path).resolve()
    if source_video is not None:
        source = Path(source_video).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"synthetic clean A-roll missing: {source}")
        if session.exists():
            raise FileExistsError("full large-v3 session root already exists; refusing to overwrite history")
        session.mkdir(parents=True)
        shutil.copy2(source, session / source.name)
    elif not session.is_dir():
        raise FileNotFoundError("session root must already contain one non-private synthetic Clean A-roll")

    child_result = session / "large-v3-session-result.json"
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "_session-child",
        "--session-root", str(session),
        "--repo-root", str(root),
        "--result-path", str(child_result),
    ]
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    records = []
    output_root = session / "DeepTalk-Aligned-Edit"
    while process.poll() is None:
        records.append(monitor_snapshot(pid=process.pid, elapsed_seconds=time.monotonic() - started, alive=True, output_bytes=_output_bytes(output_root), stage="canonical_edit_bridge_session"))
        _write_json(monitor, {"artifact_version": "local-whisper-large-v3-session-monitor/1", "records": records})
        time.sleep(max(0.1, float(poll_interval)))
    records.append(monitor_snapshot(pid=process.pid, elapsed_seconds=time.monotonic() - started, alive=False, output_bytes=_output_bytes(output_root), stage="canonical_edit_bridge_session"))
    child = json.loads(child_result.read_text(encoding="utf-8")) if child_result.is_file() else {"status": "FAILED", "error": "child did not write terminal evidence"}
    result = {
        "artifact_version": "local-whisper-large-v3-full-session/1",
        "created_at": _now(),
        "session_root": str(session),
        "child_exit_code": process.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "monitor_records": records,
        "child_result": child,
    }
    result["artifact_digest"] = canonical_digest(result)
    _write_json(monitor, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--audio", required=True)
    smoke.add_argument("--reference", required=True)
    smoke.add_argument("--evidence-root", required=True)
    full = commands.add_parser("full-session")
    full.add_argument("--session-root", required=True)
    full.add_argument("--source-video", required=True)
    full.add_argument("--repo-root", required=True)
    full.add_argument("--poll-interval", type=float, default=15.0)
    child = commands.add_parser("_session-child")
    child.add_argument("--session-root", required=True)
    child.add_argument("--repo-root", required=True)
    child.add_argument("--result-path", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "smoke":
        root = Path(args.evidence_root).resolve()
        report = run_large_v3_smoke(Path(args.audio), Path(args.reference), root / "large-v3-production-smoke.json")
        print(json.dumps({"gate_status": report["gate_status"], "artifact_digest": report["artifact_digest"]}, ensure_ascii=False))
        return 0 if report["gate_status"] == "PASS" else 2
    if args.command == "full-session":
        session = Path(args.session_root)
        result = run_full_large_v3_session(session, Path(args.repo_root), session / "large-v3-session-monitor.json", source_video=Path(args.source_video), poll_interval=args.poll_interval)
        print(json.dumps({"status": result["child_result"].get("status"), "artifact_digest": result["artifact_digest"]}, ensure_ascii=False))
        return 0 if result["child_result"].get("status") == "PASS" else 2
    return _run_session_child(Path(args.session_root), Path(args.repo_root), Path(args.result_path))


if __name__ == "__main__":
    raise SystemExit(main())
