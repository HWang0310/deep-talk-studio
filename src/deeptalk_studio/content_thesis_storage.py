"""Immutable local storage for Content Thesis Cards and Thesis Reviews."""

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .content_director import validate_content_thesis_card
from .content_thesis_renderer import render_content_thesis_card_markdown
from .content_thesis_review import validate_content_thesis_review
from .models import ContentThesisCard, ResearchReport


class ContentThesisStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContentThesisPaths:
    json: Path
    user_review: Path


@dataclass(frozen=True)
class ContentThesisReviewPaths:
    json: Path


def _safe_identifier(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    safe = re.sub(r"[^0-9A-Za-z._-]+", "-", normalized).strip("-.")
    return safe[:120] or "artifact"


def _directory(card: ContentThesisCard, output_root: Path) -> Path:
    try:
        created = datetime.fromisoformat(card.created_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ContentThesisStorageError("created_at 必须是 ISO 8601 日期时间") from exc
    return (
        Path(output_root) / f"{created.year:04d}" / f"{created.month:02d}" / f"{created.day:02d}"
        / _safe_identifier(card.report_id) / _safe_identifier(card.card_id)
    )


def save_content_thesis_card(
    card: ContentThesisCard,
    report: ResearchReport,
    profile: Mapping[str, Any],
    output_root: Path,
    review_artifact: Mapping[str, Any] | None = None,
) -> ContentThesisPaths:
    validate_content_thesis_card(card, report, profile, review_artifact)
    directory = _directory(card, output_root)
    stem = directory / f"content-thesis-card-r{card.revision:04d}"
    paths = ContentThesisPaths(
        json=stem.with_suffix(".json"),
        user_review=stem.with_name(stem.name + ".user.md"),
    )
    if paths.json.exists() or paths.user_review.exists():
        raise ContentThesisStorageError("Content Thesis Card 已存在，不能静默覆盖")
    directory.mkdir(parents=True, exist_ok=True)
    paths.json.write_text(json.dumps(card.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths.user_review.write_text(
        render_content_thesis_card_markdown(card, report, profile, review_artifact),
        encoding="utf-8",
    )
    return paths


def save_content_thesis_review_artifact(
    artifact: Mapping[str, Any],
    card: ContentThesisCard,
    report: ResearchReport,
    profile: Mapping[str, Any],
    output_root: Path,
) -> ContentThesisReviewPaths:
    validate_content_thesis_review(artifact, card, report, profile)
    directory = _directory(card, output_root)
    path = directory / f"content-thesis-review-for-r{card.revision:04d}-{_safe_identifier(str(artifact.get('review_id', '')))}.json"
    if path.exists():
        raise ContentThesisStorageError("Content Thesis Review Artifact 已存在，不能静默覆盖")
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(artifact), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ContentThesisReviewPaths(json=path)
