"""Candidate Asset Pack: opportunity-centred creator delivery from accepted candidates.

This module is strictly additive to V1.  It reads a Candidate Portfolio (Phase 2
shape with ``opportunities``) and produces a ``candidate-asset-pack/1`` whose
entries contain only candidates satisfying **raw plugin READY + Core ACCEPTED**.

Key design rules (Phase 4 acceptance, post CORRECTION-1):

* Per-request output root: each candidate's ``local-runner://`` URI is resolved
  relative to its own generation request's output directory
  (``job_root/<request_id>/output/``), discovered via the portfolio's
  ``generation_records`` execution evidence.  No shared ``output_root``.
* Immutable staging bound to Core acceptance evidence: ``observed_sha256`` from
  ``core_acceptance`` is the trusted SHA.  Source file is re-hashed and must
  match.  Raw artifact ``sha256`` must also be consistent.  Missing
  ``observed_sha256`` → fail closed.
* No winner / best / recommended semantics — ``suggested_review_order`` is
  exposed only as "review order" (查看顺序).
* Plugin-internal metadata is never exposed to the creator.
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
# Per-request output root resolution
# ---------------------------------------------------------------------------

def _generation_output_root(
    block: Mapping[str, Any],
    candidate_entry: Mapping[str, Any],
    job_root: Path,
) -> Path:
    """Resolve the per-request output directory for a candidate's generation.

    The portfolio's ``generation_records`` list carries execution evidence
    including ``request_id``.  The adapter creates output at
    ``job_root/<request_id>/output/``.  We match by ``plugin_id``.
    """
    plugin_id = str(candidate_entry.get("plugin_id", ""))
    for record in block.get("generation_records", []):
        if not isinstance(record, Mapping):
            continue
        if str(record.get("plugin_id", "")) != plugin_id:
            continue
        execution = record.get("generation_execution")
        if not isinstance(execution, Mapping):
            continue
        request_id = str(execution.get("request_id", ""))
        if not request_id:
            continue
        output_dir = Path(job_root) / request_id / "output"
        if output_dir.is_dir():
            return output_dir
    raise CandidatePackError(
        f"无法为 plugin_id={plugin_id} 定位 generation request 输出目录"
    )


# ---------------------------------------------------------------------------
# Symlink / traversal safety
# ---------------------------------------------------------------------------

def _lexical_path_has_symlink(root: Path, relative: Path) -> bool:
    """Return True if any component of *root / relative* is a symlink."""
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


def _resolve_artifact_path(uri: str, request_output: Path) -> Path | None:
    """Resolve a ``local-runner://`` URI under a per-request output root.

    Returns the resolved real path if safe, otherwise ``None``.
    """
    if not isinstance(uri, str) or not uri.startswith("local-runner://"):
        return None
    relative = uri[len("local-runner://"):]
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        return None
    if _lexical_path_has_symlink(request_output, Path(relative)):
        return None
    try:
        root = request_output.resolve(strict=True)
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


# ---------------------------------------------------------------------------
# Destination symlink hardening
# ---------------------------------------------------------------------------

def _dest_has_symlink_ancestor(dest_root: Path) -> bool:
    """Return True if any ancestor of *dest_root* is a local symlink.

    Walks the **full** lexical chain from *dest_root* upward to the
    filesystem root, checking every component with ``is_symlink()``
    (which uses ``lstat`` — lexical, not following).

    A symlink found in the chain is classified:

    * **Local redirect** — the symlink's lexical parent and its resolved
      target's parent are the same directory (e.g.
      ``sym_parent -> real_parent`` where both are siblings under the
      same parent).  This is a user-created redirect within the staging
      area and must be **rejected**.

    * **System redirect** — the symlink's parent differs from the
      resolved target's parent (e.g. ``/var -> /private/var`` on macOS
      where ``parent=/`` but ``resolved_parent=/private``).  This is an
      OS-level transparent redirect and is **allowed** to avoid
      false-positive on normal ``TemporaryDirectory`` paths.
    """
    current = dest_root
    while True:
        try:
            if current.is_symlink():
                resolved = current.resolve(strict=False)
                lexical_parent = current.parent.resolve(strict=False)
                resolved_parent = resolved.parent
                if lexical_parent == resolved_parent:
                    # Local redirect within the same parent → reject
                    return True
                # System-level redirect (different parent) → allow
        except OSError:
            return True
        if current == current.parent:
            break
        current = current.parent
    return False


def _ensure_safe_dest(dest_root: Path) -> None:
    """Ensure the staging destination root is not a symlink and has no symlink ancestors."""
    if dest_root.is_symlink():
        raise CandidatePackError("dest_root 本身是符号链接，拒绝写入")
    if _dest_has_symlink_ancestor(dest_root):
        raise CandidatePackError("dest_root 路径链包含符号链接，拒绝写入")


# ---------------------------------------------------------------------------
# Immutable staging
# ---------------------------------------------------------------------------

def _safe_filename(candidate_id: str, index: int, suffix: str) -> str:
    """Deterministic collision-safe filename without exposing plugin internals."""
    safe_id = candidate_id.replace("/", "_").replace("\\", "_").replace("..", "_")
    return f"{safe_id}_{index:03d}{suffix}"


def _stage_media(
    source_path: Path,
    dest_root: Path,
    candidate_id: str,
    index: int,
    trusted_sha: str,
) -> tuple[Path, str]:
    """Copy *source_path* into *dest_root* immutably.

    *trusted_sha* is the Core-accepted ``observed_sha256`` — the authoritative
    hash.  The source file is re-hashed; mismatch → fail closed.  After copy,
    the destination is re-hashed; mismatch → fail closed.

    Non-overwriting: if the destination already exists with the same bytes,
    the existing path is returned; if it exists with different bytes the
    function raises :class:`CandidatePackError`.
    """
    # Verify source matches trusted SHA
    source_sha = _sha256_file(source_path)
    if source_sha != trusted_sha:
        raise CandidatePackError(
            f"源文件 SHA-256 与 Core 验收 observed_sha256 不一致: "
            f"source={source_sha}, observed={trusted_sha}"
        )

    dest_root.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix or ".mp4"
    filename = _safe_filename(candidate_id, index, suffix)
    destination = dest_root / filename

    if destination.exists() or destination.is_symlink():
        if destination.is_symlink():
            raise CandidatePackError("目标路径是符号链接，拒绝写入")
        existing_sha = _sha256_file(destination)
        if existing_sha != trusted_sha:
            raise CandidatePackError("同名候选素材已存在且内容不同，拒绝覆盖")
        return destination, existing_sha

    # Copy bytes
    shutil.copy2(source_path, destination)
    observed_sha = _sha256_file(destination)
    if observed_sha != trusted_sha:
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


def _get_trusted_sha(acceptance: Mapping[str, Any], primary: Mapping[str, Any], candidate_id: str) -> str:
    """Get the trusted SHA from Core acceptance evidence.

    * ``core_acceptance.observed_sha256`` is the authoritative hash.
    * If raw artifact ``sha256`` is present, it must match.
    * Missing ``observed_sha256`` → fail closed.
    """
    observed = str(acceptance.get("observed_sha256", ""))
    if not observed or len(observed) != 64:
        raise CandidatePackError(
            f"候选 {candidate_id} 的 core_acceptance 缺少 observed_sha256，拒绝 staging"
        )
    raw_sha = str(primary.get("sha256", ""))
    if raw_sha and raw_sha != observed:
        raise CandidatePackError(
            f"候选 {candidate_id} 的 raw artifact sha256 与 Core observed_sha256 不一致"
        )
    return observed


def _build_candidate_entry(
    opportunity_block: Mapping[str, Any],
    candidate_entry: Mapping[str, Any],
    job_root: Path,
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

    # --- Resolve per-request output root from generation execution evidence ---
    request_output = _generation_output_root(opportunity_block, candidate_entry, job_root)

    # --- Get trusted SHA from Core acceptance ---
    trusted_sha = _get_trusted_sha(acceptance, primary, str(candidate.get("candidate_id", "")))

    # --- Resolve and stage the primary media ---
    source_path = _resolve_artifact_path(str(primary.get("uri", "")), request_output)
    if source_path is None or not source_path.is_file():
        raise CandidatePackError(
            f"候选 {candidate.get('candidate_id')} 的 PRIMARY_MEDIA 无法安全解析"
        )

    staged_path, observed_sha = _stage_media(
        source_path,
        dest_root,
        str(candidate["candidate_id"]),
        ordinal,
        trusted_sha,
    )

    # --- Preview artifact (optional) ---
    preview = _preview_artifact(candidate)
    preview_locator = None
    if preview is not None:
        preview_source = _resolve_artifact_path(str(preview.get("uri", "")), request_output)
        if preview_source is not None and preview_source.is_file():
            # For preview, use the raw artifact sha256 as trusted hash
            # (Core acceptance only verifies PRIMARY_MEDIA)
            preview_trusted = str(preview.get("sha256", ""))
            if preview_trusted and len(preview_trusted) == 64:
                try:
                    preview_staged, _ = _stage_media(
                        preview_source,
                        dest_root,
                        str(candidate["candidate_id"]) + "_preview",
                        ordinal,
                        preview_trusted,
                    )
                    preview_locator = f"local-candidate-artifact://{preview_staged.name}"
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
            "observed_sha256": observed_sha,
        },
    }
    return entry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_candidate_asset_pack(
    portfolio: Mapping[str, Any],
    *,
    job_root: Path,
    dest_root: Path,
) -> dict:
    """Build a ``candidate-asset-pack/1`` from a Phase 2 Candidate Portfolio.

    Parameters
    ----------
    portfolio
        A ``candidate-portfolio/1`` artifact in Phase 2 shape (with
        ``opportunities`` list).
    job_root
        The plugin job root under which per-request ``<request_id>/output/``
        directories resolve.  Each candidate's output root is discovered from
        its generation execution evidence in the portfolio.
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

    job_root = Path(job_root)
    dest_root = Path(dest_root)

    # Harden destination symlink boundary
    _ensure_safe_dest(dest_root)

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

        ready_accepted.sort(
            key=lambda c: (
                c.get("suggested_review_order", 999),
                str(c.get("plugin_candidate", {}).get("candidate_id", "")),
            )
        )

        creator_candidates: list[dict[str, Any]] = []
        for ordinal, c in enumerate(ready_accepted, start=1):
            entry = _build_candidate_entry(block, c, job_root, dest_root, ordinal)
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
