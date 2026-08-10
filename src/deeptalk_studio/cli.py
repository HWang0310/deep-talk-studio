import argparse
import json
import os
import sys
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
from .providers.openai import OpenAIProviderError, OpenAIResponsesProvider
from .storage import ReportStorageError, save_report
from .validation import ReportValidationError, validate_report
from .workflow import (
    prepare_codex_draft,
    run_fact_check_review,
    run_research,
    run_topic_discovery,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS = REPO_ROOT / "reports"
DEFAULT_DISCOVERIES = REPO_ROOT / "discoveries"
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
    discover.add_argument("--count", type=int, default=5)
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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
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
            candidate_set = prepare_codex_discovery(raw, load_channel_profile())
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
            if not 1 <= args.count <= 5:
                raise ValueError("候选数量目前只能是 1 到 5")
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
    ) as exc:
        print(f"无法生成报告：{exc}", file=sys.stderr)
        return 2
    except OpenAIProviderError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 1
