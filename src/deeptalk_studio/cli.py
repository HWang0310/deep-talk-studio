import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from .models import ResearchReport
from .providers.openai import OpenAIProviderError, OpenAIResponsesProvider
from .storage import save_report
from .validation import ReportValidationError, validate_report
from .workflow import run_research


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS = REPO_ROOT / "reports"
SAMPLE_REPORT = REPO_ROOT / "examples" / "sample-research-report.json"


def _load_report(path: Path) -> ResearchReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    report = ResearchReport.from_dict(data)
    validate_report(report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deeptalk",
        description="DeepTalk Studio：把主题整理为可核查的 Research Report。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser("research", help="联网研究一个主题")
    research.add_argument("topic", help="要研究的事件或主题")
    research.add_argument("--output", type=Path, default=DEFAULT_REPORTS)
    research.add_argument("--model", default="gpt-5.5")

    build = subparsers.add_parser(
        "build-report", help="校验研究 JSON 并生成 Markdown/JSON 报告"
    )
    build.add_argument("input", type=Path)
    build.add_argument("--output", type=Path, default=DEFAULT_REPORTS)

    validate = subparsers.add_parser("validate", help="校验一份 Research Report JSON")
    validate.add_argument("input", type=Path)

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
            paths = run_research(args.topic, provider, args.output)
            print(f"研究报告已生成：\n- Markdown：{paths.markdown}\n- JSON：{paths.json}")
            return 0
    except (FileNotFoundError, json.JSONDecodeError, ReportValidationError, ValueError) as exc:
        print(f"无法生成报告：{exc}", file=sys.stderr)
        return 2
    except OpenAIProviderError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    return 1

