"""Research → Content Thesis Card → Thesis Gate → human confirmation."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional

from .content_director import prepare_content_thesis_card
from .content_director_profile import load_content_director_profile
from .content_thesis_renderer import render_content_thesis_review_markdown
from .content_thesis_review import approve_content_thesis_card, prepare_content_thesis_review
from .content_thesis_storage import (
    ContentThesisPaths,
    ContentThesisReviewPaths,
    save_content_thesis_card,
    save_content_thesis_review_artifact,
)
from .models import ContentThesisCard, ResearchReport


DEFAULT_CONTENT_THESIS_OUTPUT = Path(__file__).resolve().parents[2] / "content_theses"


@dataclass(frozen=True)
class PreparedContentThesisResult:
    card: ContentThesisCard
    paths: ContentThesisPaths


@dataclass(frozen=True)
class ReviewedContentThesisResult:
    artifact: dict
    paths: ContentThesisReviewPaths
    user_review: str


def _iso() -> str:
    return datetime.now().astimezone().isoformat()


def prepare_codex_content_thesis(
    content: dict,
    report: ResearchReport,
    output_root: Path = DEFAULT_CONTENT_THESIS_OUTPUT,
    profile: Optional[Mapping[str, object]] = None,
    *,
    created_at: str = "",
    card_id: str = "",
) -> PreparedContentThesisResult:
    selected = dict(profile or load_content_director_profile())
    card = prepare_content_thesis_card(
        content,
        report,
        selected,
        created_at=created_at or _iso(),
        card_id=card_id or f"CTC-{uuid.uuid4().hex}",
    )
    return PreparedContentThesisResult(
        card=card,
        paths=save_content_thesis_card(card, report, selected, output_root),
    )


def run_codex_content_thesis_review(
    content: dict,
    card: ContentThesisCard,
    report: ResearchReport,
    output_root: Path = DEFAULT_CONTENT_THESIS_OUTPUT,
    profile: Optional[Mapping[str, object]] = None,
    *,
    created_at: str = "",
    review_id: str = "",
) -> ReviewedContentThesisResult:
    selected = dict(profile or load_content_director_profile())
    artifact = prepare_content_thesis_review(
        card,
        report,
        selected,
        content,
        created_at=created_at or _iso(),
        review_id=review_id or f"CTR-{uuid.uuid4().hex}",
    )
    paths = save_content_thesis_review_artifact(artifact, card, report, selected, output_root)
    return ReviewedContentThesisResult(
        artifact=artifact,
        paths=paths,
        user_review=render_content_thesis_review_markdown(card, artifact, report, selected),
    )


def confirm_content_thesis(
    card: ContentThesisCard,
    review_artifact: dict,
    report: ResearchReport,
    output_root: Path = DEFAULT_CONTENT_THESIS_OUTPUT,
    profile: Optional[Mapping[str, object]] = None,
    *,
    confirmation: str,
    confirmed_at: str = "",
) -> PreparedContentThesisResult:
    selected = dict(profile or load_content_director_profile())
    approved = approve_content_thesis_card(
        card,
        review_artifact,
        report,
        selected,
        confirmation=confirmation,
        approved_at=confirmed_at or _iso(),
    )
    return PreparedContentThesisResult(
        card=approved,
        paths=save_content_thesis_card(approved, report, selected, output_root, review_artifact),
    )
