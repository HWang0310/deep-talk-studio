"""Core-owned one-shot subprocess adapter for the fake-only Phase 1 path."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Any, Mapping

from .visual_asset_plugin_contract import validate_generation_request, validate_generation_result, validate_suitability_request, validate_suitability_response


def run_visual_plugin(plugin: Mapping[str, Any], *, operation: str, opportunity: Mapping[str, Any], job_root: Path, proposal_id: str | None = None) -> dict:
    if operation not in {"suitability", "generation"}:
        raise ValueError("operation 必须是 suitability 或 generation")
    if operation == "generation" and (not isinstance(proposal_id, str) or not proposal_id):
        raise ValueError("generation 需要有效 proposal_id")
    request_id = "REQ-" + uuid.uuid4().hex
    request = {"contract_version": "visual-asset-plugin-contract/1", "request_id": request_id, "opportunity": dict(opportunity)}
    if operation == "generation":
        request["proposal_id"] = proposal_id
    if operation == "suitability":
        validate_suitability_request(request)
    else:
        validate_generation_request(request)
    job = Path(job_root) / request_id; output = job / "output"; job.mkdir(parents=True, exist_ok=False); output.mkdir()
    request_path = job / "request.json"; result_path = job / "result.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    command = list(plugin["argv_prefix"]) + ["--request", str(request_path), "--result", str(result_path), "--output-dir", str(output)]
    try:
        process = subprocess.Popen(command, cwd=plugin["plugin_root"], env={**os.environ, **dict(plugin.get("environment", {}))}, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        stdout, stderr = process.communicate(timeout=float(plugin["timeout_seconds"]))
    except FileNotFoundError:
        return _failure(job, "missing_executable")
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        _logs(job, stdout, stderr); return _failure(job, "timeout")
    _logs(job, stdout, stderr)
    if process.returncode:
        return _failure(job, "non_zero_exit")
    if not result_path.is_file(): return _failure(job, "missing_result")
    try:
        response = json.loads(result_path.read_text(encoding="utf-8"))
        if operation == "suitability":
            validate_suitability_response(response)
        else:
            validate_generation_result(response, opportunity)
        if response["request_id"] != request_id or response["opportunity_id"] != opportunity["opportunity_id"] or (operation == "generation" and response["proposal_id"] != proposal_id):
            raise ValueError("correlation")
    except Exception:
        return _failure(job, "invalid_result")
    return {"execution": {"status": "COMPLETED", "retryable": False, "reason": "completed", "request_id": request_id, "job_locator": f"local-plugin-job://{request_id}"}, "raw_response": response}


def _logs(job: Path, stdout: str, stderr: str) -> None:
    (job / "stdout.log").write_text(stdout[-65536:], encoding="utf-8"); (job / "stderr.log").write_text(stderr[-65536:], encoding="utf-8")


def _failure(job: Path, reason: str) -> dict:
    return {"execution": {"status": "FAILED", "retryable": True, "reason": reason, "job_locator": f"local-plugin-job://{job.name}"}, "raw_response": None}
