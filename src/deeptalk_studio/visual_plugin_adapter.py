"""Fail-closed subprocess adapter for configured visual plugins."""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .visual_asset_plugin_contract import (
    validate_generation_request,
    validate_generation_result,
    validate_suitability_request,
    validate_suitability_response,
)


class VisualPluginPreflightError(ValueError):
    def __init__(self, reason: str, evidence: Mapping[str, Any]):
        super().__init__(reason)
        self.reason = reason
        self.evidence = dict(evidence)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _locator(kind: str, request_id: str, name: str = "") -> str:
    return f"local-plugin-{kind}://{request_id}" + ("/" + name if name else "")


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _configured_environment(plugin: Mapping[str, Any]) -> dict[str, str]:
    return dict(plugin.get("environment", {}))


def _process_environment(plugin: Mapping[str, Any]) -> dict[str, str]:
    return {**os.environ, **_configured_environment(plugin)}


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _preflight_template(plugin: Mapping[str, Any], resolved_root: str = "") -> dict:
    return {
        "resolved_plugin_root": resolved_root,
        "expected_source_revision": str(plugin.get("expected_source_revision", "")),
        "actual_source_revision": "",
        "require_clean_worktree": bool(plugin.get("require_clean_worktree", False)),
        "clean_worktree": None,
    }


def preflight_visual_plugin(plugin: Mapping[str, Any]) -> dict:
    """Resolve and verify a configured checkout before any plugin command runs."""
    raw_root = plugin.get("plugin_root")
    evidence = _preflight_template(plugin)
    try:
        if not isinstance(raw_root, str) or not raw_root.strip():
            raise OSError("empty plugin root")
        root = Path(raw_root).expanduser().resolve(strict=True)
        evidence["resolved_plugin_root"] = str(root)
        if not root.is_dir():
            raise OSError("plugin root is not a directory")
    except OSError as exc:
        raise VisualPluginPreflightError("plugin_root_unresolvable", evidence) from exc

    expected = evidence["expected_source_revision"]
    if re.fullmatch(r"[0-9a-f]{40}", expected) is None:
        raise VisualPluginPreflightError("expected_source_revision_invalid", evidence)

    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
            timeout=10, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise VisualPluginPreflightError("source_revision_unavailable", evidence) from exc
    evidence["actual_source_revision"] = revision
    if revision != expected:
        raise VisualPluginPreflightError("source_revision_mismatch", evidence)

    try:
        dirty = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=root, capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise VisualPluginPreflightError("clean_worktree_verification_failed", evidence) from exc
    evidence["clean_worktree"] = not bool(dirty)
    if evidence["require_clean_worktree"] and not evidence["clean_worktree"]:
        raise VisualPluginPreflightError("dirty_worktree", evidence)
    return evidence


def resolve_plugin_version(plugin: Mapping[str, Any], *, preflight: Mapping[str, Any] | None = None) -> str:
    evidence = dict(preflight) if preflight is not None else preflight_visual_plugin(plugin)
    try:
        result = subprocess.run(
            list(plugin["plugin_version_command"]),
            cwd=evidence["resolved_plugin_root"],
            env=_process_environment(plugin),
            capture_output=True,
            text=True,
            timeout=float(plugin["timeout_seconds"]),
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("plugin_version_resolution_failed") from exc
    version = result.stdout.strip()
    if not version or "\n" in version:
        raise ValueError("plugin_version_invalid")
    expected = plugin.get("plugin_version")
    if expected is not None and version != expected:
        raise ValueError("plugin_version_mismatch")
    return version


def run_visual_plugin(
    plugin: Mapping[str, Any], *, operation: str, opportunity: Mapping[str, Any],
    job_root: Path, proposal_id: str | None = None, plugin_config_digest: str = "",
    task_id: str = "UNSPECIFIED",
) -> dict:
    if operation not in {"suitability", "generation"}:
        raise ValueError("operation 必须是 suitability 或 generation")
    if operation == "generation" and (not isinstance(proposal_id, str) or not proposal_id):
        raise ValueError("generation 需要有效 proposal_id")

    request_id = "REQ-" + uuid.uuid4().hex
    started = _iso()
    started_clock = time.monotonic()
    job = Path(job_root).resolve() / request_id
    output = job / "output"
    job.mkdir(parents=True, exist_ok=False)
    output.mkdir()
    preflight = _preflight_template(plugin)
    try:
        preflight = preflight_visual_plugin(plugin)
    except VisualPluginPreflightError as exc:
        return _failure(
            plugin, request_id, operation, job, started, started_clock, exc.reason,
            plugin_config_digest, task_id=task_id, preflight=exc.evidence,
        )
    try:
        version = resolve_plugin_version(plugin, preflight=preflight)
        preflight["reported_plugin_version"] = version
    except ValueError as exc:
        return _failure(
            plugin, request_id, operation, job, started, started_clock, str(exc),
            plugin_config_digest, task_id=task_id, preflight=preflight,
        )

    request = {
        "contract_version": "visual-asset-plugin-contract/1",
        "request_id": request_id,
        "opportunity": dict(opportunity),
    }
    if operation == "generation":
        request["proposal_id"] = proposal_id
        validate_generation_request(request)
    else:
        validate_suitability_request(request)
    request_path = job / "request.json"
    result_path = job / "result.json"
    request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    command = list(plugin["argv_prefix"]) + [
        "--request", str(request_path), "--result", str(result_path),
        "--output-dir", str(output),
    ]
    try:
        process = subprocess.Popen(
            command, cwd=preflight["resolved_plugin_root"], env=_process_environment(plugin),
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
        stdout, stderr = process.communicate(timeout=float(plugin["timeout_seconds"]))
    except OSError:
        return _failure(
            plugin, request_id, operation, job, started, started_clock, "launch_failed",
            plugin_config_digest, version, task_id=task_id, preflight=preflight,
            command=command, request=request,
        )
    except subprocess.TimeoutExpired:
        termination = {
            "terminate_signal": int(signal.SIGTERM), "kill_signal": None,
            "escalated": False, "reaped": False, "process_group_terminated": False,
        }
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            stdout = stderr = None
        if _process_group_exists(process.pid):
            termination["escalated"] = True
            termination["kill_signal"] = int(signal.SIGKILL)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout, stderr = process.communicate()
        deadline = time.monotonic() + 2
        while _process_group_exists(process.pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        termination["reaped"] = process.poll() is not None
        termination["process_group_terminated"] = not _process_group_exists(process.pid)
        _logs(job, stdout, stderr)
        return _failure(
            plugin, request_id, operation, job, started, started_clock, "timeout",
            plugin_config_digest, version, task_id=task_id, preflight=preflight,
            command=command, request=request, termination=termination,
        )

    _logs(job, stdout, stderr)
    if process.returncode:
        return _failure(
            plugin, request_id, operation, job, started, started_clock, "non_zero_exit",
            plugin_config_digest, version, task_id=task_id, preflight=preflight,
            command=command, request=request,
        )
    if not result_path.is_file():
        return _failure(
            plugin, request_id, operation, job, started, started_clock, "missing_result",
            plugin_config_digest, version, task_id=task_id, preflight=preflight,
            command=command, request=request,
        )
    try:
        response = json.loads(result_path.read_text(encoding="utf-8"))
        if operation == "suitability":
            validate_suitability_response(response)
        else:
            validate_generation_result(response, opportunity)
        if (
            response["request_id"] != request_id
            or response["opportunity_id"] != opportunity["opportunity_id"]
            or response["plugin_id"] != plugin["plugin_id"]
            or response["plugin_version"] != version
            or (operation == "generation" and response["proposal_id"] != proposal_id)
        ):
            raise ValueError("correlation")
    except Exception:
        return _failure(
            plugin, request_id, operation, job, started, started_clock, "invalid_result",
            plugin_config_digest, version, task_id=task_id, preflight=preflight,
            command=command, request=request,
        )
    return {
        "execution": _execution(
            plugin, version, plugin_config_digest, request_id, operation, job,
            started, started_clock, "COMPLETED", False, "completed",
            task_id=task_id, preflight=preflight, command=command,
            request=request, response=response,
        ),
        "raw_response": response,
        "request_snapshot": request,
        "_output_root": str(output),
    }


def _identity(value: Mapping[str, Any] | None) -> dict | None:
    if value is None:
        return None
    fields = ("contract_version", "request_id", "opportunity_id", "proposal_id", "plugin_id", "plugin_version")
    result = {field: value[field] for field in fields if field in value}
    opportunity = value.get("opportunity")
    if isinstance(opportunity, Mapping) and "opportunity_id" in opportunity:
        result["opportunity_id"] = opportunity["opportunity_id"]
    return result


def _execution(
    plugin: Mapping[str, Any], version: str, config_digest: str, request_id: str,
    operation: str, job: Path, started: str, started_clock: float, status: str,
    retryable: bool, reason: str, *, task_id: str, preflight: Mapping[str, Any],
    command: list[str] | None = None, request: Mapping[str, Any] | None = None,
    response: Mapping[str, Any] | None = None, termination: Mapping[str, Any] | None = None,
) -> dict:
    execution = {
        "task_id": task_id,
        "plugin_id": plugin["plugin_id"],
        "resolved_plugin_version": version,
        "config_digest": config_digest,
        "environment_digest": _digest(_configured_environment(plugin)),
        "request_id": request_id,
        "operation": operation,
        "preflight": dict(preflight),
        "configured_runner": list(plugin["argv_prefix"]),
        "configured_version_command": list(plugin["plugin_version_command"]),
        "resolved_argv": list(command or []),
        "request_identity": _identity(request),
        "result_identity": _identity(response),
        "job_locator": _locator("job", request_id),
        "request_locator": _locator("request", request_id, "request.json"),
        "result_locator": _locator("result", request_id, "result.json"),
        "stdout_locator": _locator("log", request_id, "stdout.log"),
        "stderr_locator": _locator("log", request_id, "stderr.log"),
        "output_locator": _locator("output", request_id),
        "status": status,
        "retryable": retryable,
        "reason": reason,
        "started_at": started,
        "finished_at": _iso(),
        "runtime_duration_ms": int(round((time.monotonic() - started_clock) * 1000)),
    }
    if termination is not None:
        execution["termination"] = dict(termination)
    return execution


def _logs(job: Path, stdout: str | None, stderr: str | None) -> None:
    (job / "stdout.log").write_text((stdout or "")[-65536:], encoding="utf-8")
    (job / "stderr.log").write_text((stderr or "")[-65536:], encoding="utf-8")


def _failure(
    plugin: Mapping[str, Any], request_id: str, operation: str, job: Path,
    started: str, started_clock: float, reason: str, config_digest: str,
    version: str = "", *, task_id: str, preflight: Mapping[str, Any],
    command: list[str] | None = None, request: Mapping[str, Any] | None = None,
    termination: Mapping[str, Any] | None = None,
) -> dict:
    return {
        "execution": _execution(
            plugin, version, config_digest, request_id, operation, job, started,
            started_clock, "FAILED", True, reason, task_id=task_id,
            preflight=preflight, command=command, request=request,
            termination=termination,
        ),
        "raw_response": None,
        "request_snapshot": dict(request) if request is not None else None,
        "_output_root": str(job / "output"),
    }
