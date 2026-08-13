import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from .discovery import (
    build_research_handoff,
    load_channel_profile,
    prepare_codex_discovery,
)
from .discovery_renderer import render_discovery_markdown
from .discovery_storage import load_latest_discovery, save_discovery
from .discovery_storage import DiscoveryStorageError
from .models import ResearchReport
from .migration import load_compatible_report, migrate_v01_to_v02
from .material_profile import MaterialValidationError, load_material_profile
from .material_review import MaterialReviewError
from .material_storage import MaterialStorageError, load_material_package
from .material_workflow import (
    DEFAULT_MATERIAL_ASSETS,
    DEFAULT_MATERIAL_PACKAGES,
    prepare_codex_materials,
    run_codex_material_review,
    run_material_workflow,
)
from .providers.openai import OpenAIProviderError, OpenAIResponsesProvider
from .production_profile import ProductionValidationError
from .production_renderers import RendererError
from .production_storage import ProductionStorageError
from .production_workflow import (
    DEFAULT_PRODUCTION_ASSETS,
    DEFAULT_PRODUCTION_PACKAGES,
    DEFAULT_PRODUCTION_PROJECTS,
    run_production_workflow,
)
from .storage import ReportStorageError, save_report
from .script_profile import load_script_profile, parse_target_duration
from .script_revisions import compare_script_revisions, create_script_revision
from .script_storage import ScriptStorageError, load_script, save_script
from .script_validation import ScriptValidationError
from .script_workflow import (
    DEFAULT_SCRIPT_OUTPUT,
    prepare_codex_script,
    run_codex_script_review,
    run_script_workflow,
)
from .validation import ReportValidationError, validate_report
from .workflow import (
    prepare_codex_draft,
    run_fact_check_review,
    run_report_approval,
    run_research,
    run_topic_discovery,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS = REPO_ROOT / "reports"
DEFAULT_DISCOVERIES = REPO_ROOT / "discoveries"
DEFAULT_SCRIPTS = DEFAULT_SCRIPT_OUTPUT
DEFAULT_MATERIALS = DEFAULT_MATERIAL_PACKAGES
DEFAULT_ASSETS = DEFAULT_MATERIAL_ASSETS
SAMPLE_REPORT = REPO_ROOT / "examples" / "sample-research-report.json"
CATEGORY_ALIASES = {
    "tech": "technology",
    "technology": "technology",
    "科技": "technology",
    "business": "business",
    "商业": "business",
    "social": "social",
    "社会": "social",
    "public": "public_affairs",
    "public_affairs": "public_affairs",
    "公共": "public_affairs",
    "culture": "internet_culture",
    "internet_culture": "internet_culture",
    "网络文化": "internet_culture",
}


def _load_report(path: Path) -> ResearchReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    return load_compatible_report(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deeptalk",
        description="DeepTalk Studio：研究主题，或先寻找今天值得讲的选题。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser("research", help="联网研究一个主题")
    research.add_argument("topic", help="要研究的事件或主题")
    research.add_argument("--output", type=Path, default=DEFAULT_REPORTS)
    research.add_argument("--model", default="gpt-5.6")

    discover = subparsers.add_parser("discover", help="联网寻找近期值得深度研究的候选题")
    discover.add_argument("query", nargs="?", default="今天有什么值得讲？")
    discover.add_argument("--window", default="72h")
    discover.add_argument("--category", default="")
    discover.add_argument("--output", type=Path, default=DEFAULT_DISCOVERIES)
    discover.add_argument("--model", default="gpt-5.6")

    build = subparsers.add_parser(
        "build-report", help="校验研究 JSON 并生成 Markdown/JSON 报告"
    )
    build.add_argument("input", type=Path)
    build.add_argument("--output", type=Path, default=DEFAULT_REPORTS)

    validate = subparsers.add_parser("validate", help="校验一份 Research Report JSON")
    validate.add_argument("input", type=Path)

    migrate = subparsers.add_parser("migrate", help="把 V0.1 报告迁移为 V0.2")
    migrate.add_argument("input", type=Path)
    migrate.add_argument("--output", type=Path)

    review = subparsers.add_parser(
        "review-report", help="把独立 FactCheck Artifact 应用为新的报告修订版"
    )
    review.add_argument("draft", type=Path)
    review.add_argument("artifact", type=Path)
    review.add_argument("--output", type=Path, default=DEFAULT_REPORTS)

    approve = subparsers.add_parser(
        "approve-report", help="把用户明确确认保存为新的 ready_for_script 修订版"
    )
    approve.add_argument("report", type=Path)
    approve.add_argument("--confirmation", required=True)
    approve.add_argument("--output", type=Path, default=DEFAULT_REPORTS)

    prepare_script = subparsers.add_parser(
        "prepare-script", help="把 Codex 稿件内容整理为 Script Draft 0.4"
    )
    prepare_script.add_argument("report", type=Path)
    prepare_script.add_argument("input", type=Path)
    prepare_script.add_argument("--duration", default="")
    prepare_script.add_argument("--output", type=Path, default=DEFAULT_SCRIPTS)

    review_script = subparsers.add_parser(
        "review-script", help="把独立 Script Review 应用为新的稿件修订版"
    )
    review_script.add_argument("report", type=Path)
    review_script.add_argument("script", type=Path)
    review_script.add_argument("review", type=Path)
    review_script.add_argument("--output", type=Path, default=DEFAULT_SCRIPTS)

    compare_script = subparsers.add_parser(
        "compare-script", help="比较同一稿件的两个修订版"
    )
    compare_script.add_argument("report", type=Path)
    compare_script.add_argument("first", type=Path)
    compare_script.add_argument("second", type=Path)

    revise_script = subparsers.add_parser(
        "revise-script", help="根据用户反馈创建不可覆盖的新稿件修订版"
    )
    revise_script.add_argument("report", type=Path)
    revise_script.add_argument("previous", type=Path)
    revise_script.add_argument("input", type=Path)
    revise_script.add_argument("--duration", default="")
    revise_script.add_argument("--summary", default="根据用户反馈修改稿件。")
    revise_script.add_argument("--output", type=Path, default=DEFAULT_SCRIPTS)

    write_script = subparsers.add_parser(
        "write-script", help="用 API 从已批准 Research Report 写稿并独立审查"
    )
    write_script.add_argument("report", type=Path)
    write_script.add_argument("--duration", default="")
    write_script.add_argument("--output", type=Path, default=DEFAULT_SCRIPTS)
    write_script.add_argument("--model", default="gpt-5.6")

    prepare_materials = subparsers.add_parser(
        "prepare-materials", help="为 reviewed Script 准备 Material Package 0.5"
    )
    prepare_materials.add_argument("report", type=Path)
    prepare_materials.add_argument("script", type=Path)
    prepare_materials.add_argument("input", type=Path)
    prepare_materials.add_argument("--inspection-manifest", type=Path)
    prepare_materials.add_argument("--rights-manifest", type=Path)
    prepare_materials.add_argument("--output", type=Path, default=DEFAULT_MATERIALS)
    prepare_materials.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)

    review_materials = subparsers.add_parser(
        "review-materials", help="独立审查 Material Package 并生成新修订"
    )
    review_materials.add_argument("report", type=Path)
    review_materials.add_argument("script", type=Path)
    review_materials.add_argument("package", type=Path)
    review_materials.add_argument("review", type=Path)
    review_materials.add_argument("--output", type=Path, default=DEFAULT_MATERIALS)

    materials = subparsers.add_parser(
        "materials", help="用 API 搜索素材、生成原创画面并独立审查"
    )
    materials.add_argument("report", type=Path)
    materials.add_argument("script", type=Path)
    materials.add_argument("--output", type=Path, default=DEFAULT_MATERIALS)
    materials.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    materials.add_argument("--model", default="gpt-5.6")

    produce = subparsers.add_parser(
        "produce-assets", help="从已审查素材包生成动画、粗剪预览和制作质检"
    )
    produce.add_argument("report", type=Path)
    produce.add_argument("script", type=Path)
    produce.add_argument("package", type=Path)
    produce.add_argument(
        "--renderer", choices=("auto", "remotion", "hyperframes"), default="auto"
    )
    produce.add_argument("--output", type=Path, default=DEFAULT_PRODUCTION_PACKAGES)
    produce.add_argument("--assets", type=Path, default=DEFAULT_PRODUCTION_ASSETS)
    produce.add_argument("--projects", type=Path, default=DEFAULT_PRODUCTION_PROJECTS)
    produce.add_argument("--material-assets", type=Path, default=DEFAULT_ASSETS)

    prepare = subparsers.add_parser(
        "prepare-draft", help="把 Codex 研究内容整理为带机器字段的 V0.2 Draft"
    )
    prepare.add_argument("input", type=Path)
    prepare.add_argument("--output", type=Path, default=DEFAULT_REPORTS)

    prepare_discovery = subparsers.add_parser(
        "prepare-discovery", help="把 Codex Discovery 内容整理为候选选题"
    )
    prepare_discovery.add_argument("input", type=Path)
    prepare_discovery.add_argument("--output", type=Path, default=DEFAULT_DISCOVERIES)
    prepare_discovery.add_argument("--inspection-manifest", type=Path)

    select_topic = subparsers.add_parser(
        "select-topic", help="从最新候选中按编号生成 Research Handoff"
    )
    select_topic.add_argument("selection", help="例如：1 或 研究 1")
    select_topic.add_argument("--output", type=Path, default=DEFAULT_DISCOVERIES)

    research_selected = subparsers.add_parser(
        "research-selected", help="按最新候选编号直接进入联网 Research Workflow"
    )
    research_selected.add_argument("selection", help="例如：1 或 研究 1")
    research_selected.add_argument("--discoveries", type=Path, default=DEFAULT_DISCOVERIES)
    research_selected.add_argument("--output", type=Path, default=DEFAULT_REPORTS)
    research_selected.add_argument("--model", default="gpt-5.6")

    sample = subparsers.add_parser("sample", help="生成一份离线示例报告")
    sample.add_argument("--output", type=Path, default=DEFAULT_REPORTS)
    align_video = subparsers.add_parser("align-video", help="从剪好的真人口播生成可视粗剪")
    align_video.add_argument("--session", type=Path, required=True)
    revise_bridge = subparsers.add_parser("revise-edit-bridge", help="用自然语言调整粗剪画面")
    revise_bridge.add_argument("feedback")
    revise_bridge.add_argument("--session", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "align-video":
            session = Path(args.session)
            candidates = [] if not session.exists() else [
                path for path in session.iterdir()
                if path.is_file() and not path.is_symlink() and path.suffix.casefold() in {".mp4", ".mov"}
            ]
            if not candidates:
                print("把已经剪好口气的正式真人口播视频拖进来。\nmp4 / mov 都可以。\n不需要另外录音。\n不需要自己提取音轨。\n不需要标记时间点。")
                return 0
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                print("真人口播视频已经找到，但当前转写服务尚未授权。请在 Codex 中直接把视频拖进来，我会继续完成对齐。", file=sys.stderr)
                return 2
            from .edit_bridge_session import resolve_real_edit_bridge_session, run_real_edit_bridge_session
            from .transcription.openai import OpenAISDKTranscriptionTransport, OpenAITranscriptionProvider
            import uuid
            resolved = resolve_real_edit_bridge_session(session)
            provider = OpenAITranscriptionProvider(api_key=api_key, transport=OpenAISDKTranscriptionTransport(api_key=api_key))
            result = run_real_edit_bridge_session(
                resolved, provider,
                clock=lambda: datetime.now().astimezone().isoformat(timespec="seconds"),
                id_factory=lambda kind: f"{kind}-{uuid.uuid4().hex}",
            )
            print(f"对齐粗剪已经生成：{result.preview_path}")
            return 0
        if args.command == "revise-edit-bridge":
            from .edit_bridge_session import load_real_edit_bridge_session_result,revise_real_edit_bridge_session
            previous=load_real_edit_bridge_session_result(args.session)
            result=revise_real_edit_bridge_session(previous,args.feedback,clock=lambda:datetime.now().astimezone().isoformat(timespec="seconds"))
            print(f"新的粗剪已经生成：{result.preview_path}")
            return 0
        if args.command == "validate":
            _load_report(args.input)
            print(f"报告校验通过：{args.input}")
            return 0
        if args.command == "migrate":
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            migrated = migrate_v01_to_v02(raw)
            output = args.output or args.input.with_name(args.input.stem + ".v0.2.json")
            if output.exists():
                raise ReportStorageError(f"迁移输出已经存在：{output}")
            output.write_text(
                json.dumps(migrated, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"迁移完成：{output}")
            return 0
        if args.command == "review-report":
            draft = _load_report(args.draft)
            artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
            result = run_fact_check_review(draft, artifact, args.output)
            print(
                "独立核查已应用：\n"
                f"- FactCheck Artifact：{result.fact_check}\n"
                f"- 新修订版 Markdown：{result.reviewed.markdown}\n"
                f"- 新修订版 JSON：{result.reviewed.json}\n"
                f"- 最终状态：{result.final_status}"
            )
            return 0
        if args.command == "approve-report":
            paths = run_report_approval(
                _load_report(args.report), args.confirmation, args.output
            )
            print(
                "用户确认已保存为新的 Research Revision：\n"
                f"- Markdown：{paths.markdown}\n"
                f"- JSON：{paths.json}\n"
                "该修订版现在可以进入 Original Script Agent。"
            )
            return 0
        if args.command == "prepare-script":
            report = _load_report(args.report)
            content = json.loads(args.input.read_text(encoding="utf-8"))
            result = prepare_codex_script(
                content,
                report,
                args.output,
                load_script_profile(),
                target_duration_minutes=parse_target_duration(args.duration),
            )
            print(
                "Script Draft 已生成：\n"
                f"- JSON：{result.paths.json}\n"
                f"- Editor：{result.paths.editor}\n"
                f"- Teleprompter：{result.paths.teleprompter}\n"
                "下一步必须执行独立 Script Review。"
            )
            return 0
        if args.command == "review-script":
            report = _load_report(args.report)
            profile = load_script_profile()
            script = load_script(args.script, report, profile)
            content = json.loads(args.review.read_text(encoding="utf-8"))
            result = run_codex_script_review(
                content, report, script, args.output, profile
            )
            print(
                "稿件审查已完成：\n"
                f"- Review Artifact：{result.review_artifact}\n"
                f"- 新修订版 JSON：{result.paths.json}\n"
                f"- Teleprompter：{result.paths.teleprompter}\n"
                f"- 最终状态：{result.script.status}"
            )
            return 0
        if args.command == "compare-script":
            report = _load_report(args.report)
            profile = load_script_profile()
            first = load_script(args.first, report, profile)
            second = load_script(args.second, report, profile)
            print(json.dumps(compare_script_revisions(first, second), ensure_ascii=False, indent=2))
            return 0
        if args.command == "revise-script":
            report = _load_report(args.report)
            profile = load_script_profile()
            previous = load_script(args.previous, report, profile)
            content = json.loads(args.input.read_text(encoding="utf-8"))
            target = (
                parse_target_duration(args.duration)
                if args.duration.strip()
                else previous.target_duration_minutes
            )
            revised = create_script_revision(
                content,
                previous,
                report,
                profile,
                generated_at=datetime.now().astimezone().isoformat(),
                target_duration_minutes=target,
                change_summary=args.summary,
            )
            paths = save_script(revised, report, profile, args.output)
            print(
                "新的 Script Revision 已生成：\n"
                f"- JSON：{paths.json}\n"
                f"- Editor：{paths.editor}\n"
                f"- Teleprompter：{paths.teleprompter}\n"
                "修改后的稿件必须重新执行独立 Script Review。"
            )
            return 0
        if args.command == "write-script":
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                print(
                    "没有检测到 OPENAI_API_KEY。请在 Codex 中对 reviewed 报告明确说‘确认，开始写稿’，write-script Skill 会在后台保存批准并生成稿件。",
                    file=sys.stderr,
                )
                return 2
            report = _load_report(args.report)
            result = run_script_workflow(
                report,
                OpenAIResponsesProvider(api_key=api_key, model=args.model),
                args.output,
                load_script_profile(),
                target_duration_minutes=parse_target_duration(args.duration),
            )
            print(
                "原创口播稿与独立审查已完成：\n"
                f"- Draft：{result.draft.json}\n"
                f"- Review Artifact：{result.review_artifact}\n"
                f"- 最终稿：{result.reviewed.json}\n"
                f"- Teleprompter：{result.reviewed.teleprompter}\n"
                f"- 最终状态：{result.final_status}"
            )
            return 0
        if args.command == "prepare-materials":
            report = _load_report(args.report)
            script = load_script(args.script, report, load_script_profile())
            content = json.loads(args.input.read_text(encoding="utf-8"))
            inspection = (
                json.loads(args.inspection_manifest.read_text(encoding="utf-8"))
                if args.inspection_manifest else {"entries": []}
            )
            rights = (
                json.loads(args.rights_manifest.read_text(encoding="utf-8"))
                if args.rights_manifest else {"entries": []}
            )
            result = prepare_codex_materials(
                content, script, report, args.output, args.assets,
                load_material_profile(), inspection, rights,
            )
            print(
                "素材准备单已生成：\n"
                f"- 阅读版：{result.paths.markdown}\n"
                f"- 数据版：{result.paths.json}\n"
                "下一步必须执行独立 Material Review。"
            )
            return 0
        if args.command == "review-materials":
            report = _load_report(args.report)
            profile = load_material_profile()
            script = load_script(args.script, report, load_script_profile())
            package = load_material_package(args.package, script, report, profile)
            content = json.loads(args.review.read_text(encoding="utf-8"))
            result = run_codex_material_review(
                content, package, script, report, args.output, profile
            )
            print(
                "素材独立审查已完成：\n"
                f"- Review Artifact：{result.review_artifact}\n"
                f"- 阅读版：{result.paths.markdown}\n"
                f"- 最终状态：{result.package.status}"
            )
            return 0
        if args.command == "materials":
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                print(
                    "没有检测到 OPENAI_API_KEY。你仍可在 Codex 中直接说“给这期配素材”，prepare-materials Skill 会使用当前 Codex 的联网能力。",
                    file=sys.stderr,
                )
                return 2
            report = _load_report(args.report)
            script = load_script(args.script, report, load_script_profile())
            result = run_material_workflow(
                script, report, OpenAIResponsesProvider(api_key=api_key, model=args.model),
                args.output, args.assets, load_material_profile(),
            )
            print(
                "素材搜索、原创画面和独立审查已完成：\n"
                f"- 初始包：{result.draft.markdown}\n"
                f"- Review Artifact：{result.review_artifact}\n"
                f"- 最终包：{result.reviewed.markdown}\n"
                f"- 最终状态：{result.final_status}"
            )
            return 0
        if args.command == "produce-assets":
            report = _load_report(args.report)
            script = load_script(args.script, report, load_script_profile())
            result = run_production_workflow(
                args.package, script, report,
                material_asset_root=args.material_assets,
                package_root=args.output, asset_root=args.assets,
                project_root=args.projects, renderer_mode=args.renderer,
            )
            print(
                result.summary
                + f"\n实际使用的制作引擎：{result.plan['selected_renderer']}\n"
                + f"制作质检：{result.qa['package_gate_status']}\n"
                + f"粗剪和动画素材目录：{args.assets.resolve() / result.plan['production_id'] / 'assets'}\n"
                + f"制作质检报告：{result.qa_path}\n"
            )
            return 0
        if args.command == "prepare-draft":
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            report = prepare_codex_draft(raw)
            paths = save_report(report, args.output)
            print(
                "Research Draft 已生成：\n"
                f"- Markdown：{paths.markdown}\n"
                f"- JSON：{paths.json}\n"
                "下一步必须执行独立 Fact Check。"
            )
            return 0
        if args.command == "prepare-discovery":
            raw = json.loads(args.input.read_text(encoding="utf-8"))
            manifest = (
                json.loads(args.inspection_manifest.read_text(encoding="utf-8"))
                if args.inspection_manifest
                else None
            )
            candidate_set = prepare_codex_discovery(
                raw, load_channel_profile(), inspection_manifest=manifest
            )
            paths = save_discovery(candidate_set, args.output)
            print(
                "候选选题已生成：\n"
                f"- 阅读版：{paths.markdown}\n"
                f"- 数据版：{paths.json}\n\n"
                + render_discovery_markdown(candidate_set)
            )
            return 0
        if args.command == "select-topic":
            candidate_set = load_latest_discovery(args.output)
            handoff = build_research_handoff(candidate_set, args.selection)
            print(
                f"已选择第 {handoff['selected_position']} 个选题：{handoff['title']}\n"
                "下面的结构化交接将直接供 Research Workflow 使用：\n"
                + json.dumps(handoff, ensure_ascii=False, indent=2)
            )
            return 0
        if args.command in {"build-report", "sample"}:
            source = args.input if args.command == "build-report" else SAMPLE_REPORT
            paths = save_report(_load_report(source), args.output)
            prefix = "示例报告已生成" if args.command == "sample" else "报告已生成"
            print(f"{prefix}：\n- Markdown：{paths.markdown}\n- JSON：{paths.json}")
            return 0
        if args.command == "research":
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                print(
                    "没有检测到 OPENAI_API_KEY。你仍可在 Codex 中直接说“研究某个话题”，项目 Skill 会使用当前 Codex 的联网能力。",
                    file=sys.stderr,
                )
                return 2
            provider = OpenAIResponsesProvider(api_key=api_key, model=args.model)
            result = run_research(args.topic, provider, args.output)
            print(
                "研究与独立核查已完成：\n"
                f"- Research Draft：{result.draft.json}\n"
                f"- FactCheck Artifact：{result.fact_check}\n"
                f"- 最终报告 Markdown：{result.reviewed.markdown}\n"
                f"- 最终报告 JSON：{result.reviewed.json}\n"
                f"- 最终状态：{result.final_status}"
            )
            return 0
        if args.command == "discover":
            if args.window != "72h":
                raise ValueError("V0.3 目前固定使用 72h 发现窗口")
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                print(
                    "没有检测到 OPENAI_API_KEY。你仍可在 Codex 中直接说“今天讲什么？”或“帮我找几个科技选题”，discover-topics Skill 会使用当前 Codex 的联网能力。",
                    file=sys.stderr,
                )
                return 2
            query = args.query if not args.category else f"{args.query}（只看 {args.category}）"
            category_filter = ()
            if args.category:
                category = CATEGORY_ALIASES.get(args.category.strip().casefold())
                if not category:
                    raise ValueError("暂不支持该分类，请使用 tech、business、social、public 或 culture")
                category_filter = (category,)
            provider = OpenAIResponsesProvider(api_key=api_key, model=args.model)
            result = run_topic_discovery(
                query, provider, args.output, category_filter=category_filter
            )
            print(
                "候选选题已生成：\n"
                f"- 阅读版：{result.paths.markdown}\n"
                f"- 数据版：{result.paths.json}\n\n"
                + render_discovery_markdown(result.candidate_set)
            )
            return 0
        if args.command == "research-selected":
            candidate_set = load_latest_discovery(args.discoveries)
            handoff = build_research_handoff(candidate_set, args.selection)
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                print(
                    "没有检测到 OPENAI_API_KEY。请在 Codex 中只回复选题编号，discover-topics Skill 会把已选主题直接交给 research-topic Skill。",
                    file=sys.stderr,
                )
                return 2
            provider = OpenAIResponsesProvider(api_key=api_key, model=args.model)
            result = run_research(
                handoff["title"], provider, args.output, research_handoff=handoff
            )
            print(
                "已根据选中的候选进入 Research Workflow：\n"
                f"- Research Draft：{result.draft.json}\n"
                f"- FactCheck Artifact：{result.fact_check}\n"
                f"- 最终报告：{result.reviewed.json}\n"
                f"- 最终状态：{result.final_status}"
            )
            return 0
    except (
        OSError,
        json.JSONDecodeError,
        ReportStorageError,
        ReportValidationError,
        ValueError,
        DiscoveryStorageError,
        ScriptStorageError,
        ScriptValidationError,
        MaterialValidationError,
        MaterialReviewError,
        MaterialStorageError,
        ProductionValidationError,
        ProductionStorageError,
        RendererError,
    ) as exc:
        print(f"无法生成报告：{exc}", file=sys.stderr)
        return 2
    except OpenAIProviderError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 1
