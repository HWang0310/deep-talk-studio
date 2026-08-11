"""Reviewed Script → Material Package → original SVG → independent Review."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional

from .material_profile import load_material_profile
from .material_review import MaterialReviewResult, prepare_material_review
from .material_review import MaterialReviewError
from .material_schema import MATERIAL_CONTENT_JSON_SCHEMA, MATERIAL_REVIEW_CONTENT_JSON_SCHEMA
from .material_storage import (
    MaterialPaths, save_material_package, save_material_review_artifact,
)
from .material_validation import (
    apply_provider_search_provenance, prepare_material_package, update_package_assets,
    validate_material_inputs,
)
from .models import MaterialPackage
from .providers.base import MaterialProvider
from .visual_renderer import render_visual_svg, visual_asset_record


DEFAULT_MATERIAL_PACKAGES = Path(__file__).resolve().parents[2] / "material_packages"
DEFAULT_MATERIAL_ASSETS = Path(__file__).resolve().parents[2] / "material_assets"


@dataclass(frozen=True)
class PreparedMaterialResult:
    package: MaterialPackage
    paths: MaterialPaths


@dataclass(frozen=True)
class ReviewedMaterialResult:
    artifact: dict
    review_artifact: Path
    package: MaterialPackage
    paths: MaterialPaths


@dataclass(frozen=True)
class MaterialWorkflowResult:
    draft: MaterialPaths
    review_artifact: Path
    reviewed: MaterialPaths
    package_id: str
    final_status: str


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def prepare_codex_materials(
    content: dict, script: object, report: object,
    package_root: Path = DEFAULT_MATERIAL_PACKAGES,
    asset_root: Path = DEFAULT_MATERIAL_ASSETS,
    profile: Optional[Mapping[str, object]] = None,
    inspection_manifest: Optional[Mapping[str, object]] = None,
    rights_manifest: Optional[Mapping[str, object]] = None,
    *, created_at: str = "", package_id: str = "",
) -> PreparedMaterialResult:
    selected = dict(profile or load_material_profile())
    package = prepare_material_package(
        content, script, report, selected,
        inspection_manifest=inspection_manifest, rights_manifest=rights_manifest,
        created_at=created_at or _now(), package_id=package_id or f"MAT-{uuid.uuid4().hex}",
        package_mode="codex_skill",
    )
    visual_records = {}
    visual_directory = Path(asset_root) / package.package_id / "generated"
    for spec in package.generated_visuals:
        path = render_visual_svg(spec, visual_directory)
        visual_records[spec["visual_id"]] = visual_asset_record(path)
    package = update_package_assets(package, visual_records=visual_records)
    return PreparedMaterialResult(package, save_material_package(package, package_root))


def run_codex_material_review(
    content: dict, package: MaterialPackage, script: object, report: object,
    package_root: Path = DEFAULT_MATERIAL_PACKAGES,
    profile: Optional[Mapping[str, object]] = None,
    *, created_at: str = "", review_id: str = "",
) -> ReviewedMaterialResult:
    selected = dict(profile or load_material_profile())
    review = prepare_material_review(
        content, package, script, report, selected,
        created_at=created_at or _now(), review_id=review_id or f"MRV-{uuid.uuid4().hex}",
        review_mode="codex_skill",
    )
    artifact_path = save_material_review_artifact(review.artifact, package, package_root)
    paths = save_material_package(review.package, package_root)
    return ReviewedMaterialResult(review.artifact, artifact_path, review.package, paths)


def run_material_workflow(
    script: object, report: object, provider: MaterialProvider,
    package_root: Path = DEFAULT_MATERIAL_PACKAGES,
    asset_root: Path = DEFAULT_MATERIAL_ASSETS,
    profile: Optional[Mapping[str, object]] = None,
    *, clock=lambda: datetime.now().astimezone().isoformat(),
    id_factory=lambda prefix: f"{prefix}-{uuid.uuid4().hex}",
) -> MaterialWorkflowResult:
    selected = dict(profile or load_material_profile())
    validate_material_inputs(script, report, selected, getattr(script, "review_artifact", None))
    search = provider.search_materials(
        script.to_dict(), report.to_dict(), selected, MATERIAL_CONTENT_JSON_SCHEMA
    )
    package = prepare_material_package(
        search.data, script, report, selected, inspection_manifest={"entries": []},
        rights_manifest={"entries": []}, created_at=clock(), package_id=id_factory("MAT"),
        package_mode="openai_api",
    )
    package = apply_provider_search_provenance(package, search.provenance)
    visual_records = {}
    visual_directory = Path(asset_root) / package.package_id / "generated"
    for spec in package.generated_visuals:
        path = render_visual_svg(spec, visual_directory)
        visual_records[spec["visual_id"]] = visual_asset_record(path)
    package = update_package_assets(package, visual_records=visual_records)
    draft_paths = save_material_package(package, package_root)
    review_result = provider.review_materials(
        package.to_dict(), script.to_dict(), report.to_dict(), MATERIAL_REVIEW_CONTENT_JSON_SCHEMA
    )
    if review_result.provenance.search_calls or review_result.provenance.citations:
        raise MaterialReviewError("Material Reviewer 不得扩展搜索或 Research")
    review = prepare_material_review(
        review_result.data, package, script, report, selected,
        created_at=clock(), review_id=id_factory("MRV"), review_mode="openai_api",
    )
    artifact_path = save_material_review_artifact(review.artifact, package, package_root)
    reviewed_paths = save_material_package(review.package, package_root)
    return MaterialWorkflowResult(
        draft_paths, artifact_path, reviewed_paths, package.package_id, review.package.status
    )
