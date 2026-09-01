"""Candidate Asset Pack: opportunity-centred creator delivery from accepted candidates.

This module is strictly additive to V1.  It reads a Candidate Portfolio (Phase 2
shape with ``opportunities``) and produces a ``candidate-asset-pack/1`` whose
entries contain only candidates satisfying **raw plugin READY + Core ACCEPTED**.

Key design rules (Phase 4 acceptance):

* Machine history (failed, rejected, no-call) stays in the portfolio; it is
  never copied into the creator pack.
* No winner / best / recommended semantics — ``suggested_review_order`` is
  exposed only as "review order" (查看顺序).
* Immutable staging: PRIMARY_MEDIA bytes are copied into a Core-owned
  candidate asset root.  Filenames are deterministic and collision-safe;
  existing files with differing bytes cause a fail-closed error.
* Plugin-internal metadata (``plugin_metadata``, opaque debug fields, runner
  argv, process logs) is never exposed to the creator.
* No A-roll modification, no NLE project, no finished video generation.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence


class CandidatePackError(ValueError):
    """The candidate asset pack cannot be safely assembled."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tc(ms: int) -> str:
    """Render milliseconds as ``HH:MM:SS.mmm`` timecode."""
    if ms < 0:
        ms = 0
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def _is_ready_accepted(entry: Mapping[str, Any]) -> bool:
    candidate = entry.get("plugin_candidate")
    acceptance = entry.get("core_acceptance")
    return (
        isinstance(candidate, Mapping)
        and candidate.get("candidate_status") == "READY"
        and isinstance(acceptance, Mapping)
        and acceptance.get("status") == "ACCEPTED"
    )


def _primary_artifact(candidate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for artifact in candidate.get("artifacts", []):
        if isinstance(artifact, Mapping) and artifact.get("role") == "PRIMARY_MEDIA":
            return artifact
    return None


def _preview_artifact(candidate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for artifact in candidate.get("artifacts", []):
        if isinstance(artifact, Mapping) and artifact.get("role") == "PREVIEW":
            return artifact
    return None


# ---------------------------------------------------------------------------
# Immutable staging
# ---------------------------------------------------------------------------

def _safe_filename(candidate_id: str, index: int, suffix: str) -> str:
    """Deterministic collision-safe filename without exposing plugin internals."""
    safe_id = candidate_id.replace("/", "_").replace("\\", "_").replace("..", "_")
    return f"{safe_id}_{index:03d}{suffix}"


def _lexical_path_has_symlink(root: Path, relative: Path) -> bool:
    paths: list[Path] = [root]
    current = root
    for part in relative.parts:
        current = current / part
        paths.append(current)
    for path in paths:
        try:
            if stat.S_ISLNK(path.lstat().st_mode):
                return True
        except FileNotFoundError:
            continue
        except OSError:
            return True
    return False


def _resolve_artifact_path(
    uri: str,
    output_root: Path,
) -> Path | None:
    """Resolve a ``local-runner://`` URI under the plugin output root.

    Returns the resolved real path if safe, otherwise ``None``.
    """
    if not isinstance(uri, str) or not uri.startswith("local-runner://"):
        return None
    relative = uri[len("local-runner://"):]
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        return None
    if _lexical_path_has_symlink(output_root, Path(relative)):
        return None
    try:
        root = output_root.resolve(strict=True)
        candidate = (root / relative).resolve(strict=False)
    except OSError:
        return None
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.is_symlink():
        return None
    return candidate


def _stage_media(
    source_path: Path,
    dest_root: Path,
    candidate_id: str,
    index: int,
    expected_sha: str,
) -> tuple[Path, str]:
    """Copy *source_path* into *dest_root* immutably.

    Non-overwriting: if the destination already exists with the same bytes,
    the existing path is returned; if it exists with different bytes the
    function raises :class:`CandidatePackError`.
    """
    dest_root.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix or ".mp4"
    filename = _safe_filename(candidate_id, index, suffix)
    destination = dest_root / filename

    if destination.exists() or destination.is_symlink():
        if destination.is_symlink():
            raise CandidatePackError("目标路径是符号链接，拒绝写入")
        existing_sha = _sha256_file(destination)
        if existing_sha != expected_sha:
            raise CandidatePackError("同名候选素材已存在且内容不同，拒绝覆盖")
        return destination, existing_sha

    # Copy bytes
    shutil.copy2(source_path, destination)
    observed_sha = _sha256_file(destination)
    if observed_sha != expected_sha:
        # Remove the bad copy to avoid leaving corrupted state
        try:
            destination.unlink()
        except OSError:
            pass
        raise CandidatePackError("候选素材复制后 SHA-256 校验失败")
    return destination, observed_sha


# ---------------------------------------------------------------------------
# Creator-facing candidate entry
# ---------------------------------------------------------------------------

def _creator_qa_summary(candidate: Mapping[str, Any]) -> dict:
    qa = candidate.get("qa", {})
    if not isinstance(qa, Mapping):
        return {"status": "UNKNOWN", "summary": ""}
    return {
        "status": str(qa.get("status", "")),
        "summary": str(qa.get("summary", "")),
    }


def _creator_provenance(candidate: Mapping[str, Any]) -> dict:
    prov = candidate.get("provenance", {})
    if not isinstance(prov, Mapping):
        return {"origin": "", "source_ref": ""}
    return {
        "origin": str(prov.get("origin", "")),
        "source_ref": str(prov.get("source_ref", "")),
    }


def _build_candidate_entry(
    opportunity_block: Mapping[str, Any],
    candidate_entry: Mapping[str, Any],
    output_root: Path,
    dest_root: Path,
    ordinal: int,
) -> dict:
    """Build a single creator-facing candidate entry with staged media."""
    opportunity = opportunity_block["opportunity"]
    candidate = candidate_entry["plugin_candidate"]
    acceptance = candidate_entry["core_acceptance"]
    primary = _primary_artifact(candidate)
    if primary is None:
        raise CandidatePackError(
            f"READY/ACCEPTED candidate {candidate.get('candidate_id')} lacks PRIMARY_MEDIA"
        )

    # Resolve and stage the primary media
    source_path = _resolve_artifact_path(str(primary.get("uri", "")), output_root)
    if source_path is None or not source_path.is_file():
        raise CandidatePackError(
            f"候选 {candidate.get('candidate_id')} 的 PRIMARY_MEDIA 无法安全解析"
        )
    expected_sha = str(primary.get("sha256", ""))
    if not expected_sha:
        expected_sha = _sha256_file(source_path)

    staged_path, observed_sha = _stage_media(
        source_path,
        dest_root,
        str(candidate["candidate_id"]),
        ordinal,
        expected_sha,
    )

    # Preview artifact (optional)
    preview = _preview_artifact(candidate)
    preview_locator = None
    if preview is not None:
        preview_source = _resolve_artifact_path(str(preview.get("uri", "")), output_root)
        if preview_source is not None and preview_source.is_file():
            preview_suffix = preview_source.suffix or ".png"
            preview_filename = _safe_filename(
                str(candidate["candidate_id"]), ordinal, preview_suffix
            )
            try:
                _, _ = _stage_media(
                    preview_source,
                    dest_root,
                    str(candidate["candidate_id"]) + "_preview",
                    ordinal,
                    str(preview.get("sha256", "")) or _sha256_file(preview_source),
                )
                preview_locator = f"local-candidate-artifact://{preview_filename}"
            except CandidatePackError:
                preview_locator = None

    window = opportunity.get("a_roll_window", {})
    placement = candidate.get("suggested_placement", {})

    entry: dict[str, Any] = {
        "candidate_id": str(candidate["candidate_id"]),
        "asset_family": str(candidate.get("asset_family", "")),
        "duration_ms": int(candidate.get("duration_ms", 0)),
        "duration_timecode": _tc(int(candidate.get("duration_ms", 0))),
        "suggested_placement": {
            "start_ms": int(placement.get("start_ms", 0)),
            "end_ms": int(placement.get("end_ms", 0)),
            "start_timecode": _tc(int(placement.get("start_ms", 0))),
            "end_timecode": _tc(int(placement.get("end_ms", 0))),
        },
        "a_roll_window": {
            "start_ms": int(window.get("start_ms", 0)),
            "end_ms": int(window.get("end_ms", 0)),
            "start_timecode": _tc(int(window.get("start_ms", 0))),
            "end_timecode": _tc(int(window.get("end_ms", 0))),
        },
        "opportunity_purpose": str(opportunity.get("visual_purpose", "")),
        "opportunity_reason": str(opportunity.get("semantic_context", "")),
        "qa_summary": _creator_qa_summary(candidate),
        "provenance": _creator_provenance(candidate),
        "primary_media": {
            "filename": staged_path.name,
            "media_type": str(primary.get("media_type", "video/mp4")),
            "sha256": observed_sha,
            "staged_path": str(staged_path),
            "locator": f"local-candidate-artifact://{staged_path.name}",
        },
        "preview_media": {"locator": preview_locator} if preview_locator else None,
        "review_order": ordinal,
        "core_acceptance_provenance": {
            "status": str(acceptance.get("status", "")),
        },
    }
    return entry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_candidate_asset_pack(
    portfolio: Mapping[str, Any],
    *,
    output_root: Path,
    dest_root: Path,
) -> dict:
    """Build a ``candidate-asset-pack/1`` from a Phase 2 Candidate Portfolio.

    Parameters
    ----------
    portfolio
        A ``candidate-portfolio/1`` artifact in Phase 2 shape (with
        ``opportunities`` list).
    output_root
        The plugin job root under which ``local-runner://`` URIs resolve.
    dest_root
        Core-owned immutable staging destination for candidate media.

    Returns
    -------
    dict
        ``candidate-asset-pack/1`` artifact with opportunity-centred entries
        containing only READY + ACCEPTED candidates.
    """
    if portfolio.get("artifact_version") != "candidate-portfolio/1":
        raise CandidatePackError("只接受 candidate-portfolio/1")
    if not isinstance(portfolio.get("opportunities"), list):
        raise CandidatePackError("portfolio 缺少 opportunities 列表")

    opportunity_entries: list[dict[str, Any]] = []

    for block in portfolio["opportunities"]:
        if not isinstance(block, Mapping) or "opportunity" not in block:
            continue
        opportunity = block["opportunity"]
        candidates = block.get("candidates", [])
        ready_accepted = [
            c for c in candidates if isinstance(c, Mapping) and _is_ready_accepted(c)
        ]
        if not ready_accepted:
            # Zero candidates for this opportunity — still include the
            # opportunity in the pack with an empty candidate list.
            opportunity_entries.append({
                "opportunity_id": str(opportunity.get("opportunity_id", "")),
                "a_roll_window": {
                    "start_ms": int(opportunity.get("a_roll_window", {}).get("start_ms", 0)),
                    "end_ms": int(opportunity.get("a_roll_window", {}).get("end_ms", 0)),
                    "start_timecode": _tc(int(opportunity.get("a_roll_window", {}).get("start_ms", 0))),
                    "end_timecode": _tc(int(opportunity.get("a_roll_window", {}).get("end_ms", 0))),
                },
                "visual_purpose": str(opportunity.get("visual_purpose", "")),
                "semantic_context": str(opportunity.get("semantic_context", "")),
                "candidates": [],
            })
            continue

        # Sort ready/accepted candidates by suggested_review_order if present,
        # otherwise by candidate_id for determinism.
        ready_accepted.sort(
            key=lambda c: (
                c.get("suggested_review_order", 999),
                str(c.get("plugin_candidate", {}).get("candidate_id", "")),
            )
        )

        creator_candidates: list[dict[str, Any]] = []
        for ordinal, c in enumerate(ready_accepted, start=1):
            entry = _build_candidate_entry(block, c, Path(output_root), Path(dest_root), ordinal)
            creator_candidates.append(entry)

        opportunity_entries.append({
            "opportunity_id": str(opportunity.get("opportunity_id", "")),
            "a_roll_window": {
                "start_ms": int(opportunity.get("a_roll_window", {}).get("start_ms", 0)),
                "end_ms": int(opportunity.get("a_roll_window", {}).get("end_ms", 0)),
                "start_timecode": _tc(int(opportunity.get("a_roll_window", {}).get("start_ms", 0))),
                "end_timecode": _tc(int(opportunity.get("a_roll_window", {}).get("end_ms", 0))),
            },
            "visual_purpose": str(opportunity.get("visual_purpose", "")),
            "semantic_context": str(opportunity.get("semantic_context", "")),
            "candidates": creator_candidates,
        })

    pack: dict[str, Any] = {
        "artifact_version": "candidate-asset-pack/1",
        "source_portfolio_id": str(portfolio.get("portfolio_id", "")),
        "source_portfolio_digest": str(portfolio.get("portfolio_digest", "")),
        "opportunities": opportunity_entries,
    }
    pack["pack_digest"] = _digest(pack)
    return pack


def save_candidate_asset_pack(pack: Mapping[str, Any], dest_dir: Path) -> Path:
    """Write the candidate asset pack JSON to *dest_dir*.

    Non-overwriting: uses a deterministic filename derived from the pack
    digest prefix.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    digest = str(pack.get("pack_digest", ""))
    if len(digest) < 16:
        raise CandidatePackError("pack digest 无效")
    filename = f"candidate-asset-pack-{digest[:16]}.json"
    path = dest_dir / filename
    if path.exists():
        if path.is_symlink():
            raise CandidatePackError("目标路径是符号链接，拒绝写入")
        raise CandidatePackError("不会覆盖已有工件")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(pack, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
    return path
