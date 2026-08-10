"""Non-overwriting persistence for Topic Candidate Set history and latest pointer."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .discovery_renderer import render_discovery_markdown
from .discovery_validation import DiscoveryValidationError, validate_candidate_set
from .models import TopicCandidateSet
from .storage import _safe_identifier


class DiscoveryStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiscoveryPaths:
    json: Path
    markdown: Path
    latest_manifest: Path


def _date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DiscoveryStorageError("generated_at 必须是 ISO 8601 日期时间") from None


def save_discovery(candidate_set: TopicCandidateSet, output_root: Path) -> DiscoveryPaths:
    validate_candidate_set(candidate_set)
    moment = _date(candidate_set.generated_at)
    directory = (
        Path(output_root)
        / f"{moment.year:04d}"
        / f"{moment.month:02d}"
        / f"{moment.day:02d}"
    )
    base = directory / _safe_identifier(candidate_set.discovery_id)
    json_path = base.with_suffix(".json")
    markdown_path = base.with_suffix(".md")
    if json_path.exists() or markdown_path.exists():
        raise DiscoveryStorageError(f"Discovery {candidate_set.discovery_id} 已经存在，不能静默覆盖")
    directory.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(candidate_set.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_discovery_markdown(candidate_set), encoding="utf-8")
    latest = Path(output_root) / "latest.json"
    latest.write_text(
        json.dumps(
            {"discovery_id": candidate_set.discovery_id, "artifact_path": str(json_path)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return DiscoveryPaths(json=json_path, markdown=markdown_path, latest_manifest=latest)


def load_latest_discovery(output_root: Path) -> TopicCandidateSet:
    latest = Path(output_root) / "latest.json"
    try:
        pointer = json.loads(latest.read_text(encoding="utf-8"))
        path = Path(pointer["artifact_path"])
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DiscoveryStorageError("没有可供选择的最新选题，请先执行一次 Discovery。") from exc
    try:
        candidate_set = TopicCandidateSet.from_dict(data)
    except DiscoveryValidationError as exc:
        raise DiscoveryStorageError(f"最新选题文件无法使用：{exc}") from None
    if candidate_set.discovery_id != pointer["discovery_id"]:
        raise DiscoveryStorageError("最新选题指针与文件不一致，请重新执行 Discovery。")
    return candidate_set
