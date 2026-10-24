"""Creator Workbench (Issue #23) tests: settings, acquisition, full loop.

The full-loop test drives the real engine chain (research draft → fact check
→ approval → thesis → review → approval → script + review) with a scripted
LLM provider, fake fetcher and fake media runners, asserting that every
canonical artifact lands in the engine trees and that the fail-closed gates
actually block bad LLM output (invented chat-mode sources, ungrounded
fact-check quotes).
"""

import io
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deeptalk_studio.providers.base import ProviderResult
from deeptalk_studio.provenance import ProviderProvenance
from deeptalk_studio.schema import (
    API_RESEARCH_DRAFT_JSON_SCHEMA,
    FACT_CHECK_JSON_SCHEMA,
    SCRIPT_DRAFT_CONTENT_JSON_SCHEMA,
    SCRIPT_REVIEW_CHECK_NAMES,
    THESIS_CONTENT_JSON_SCHEMA,
)
from deeptalk_studio.validation import validate_json_schema
from deeptalk_studio.workbench import acquisition
from deeptalk_studio.workbench.creative_chat import CreativeChatStore, CreativeChatError
from deeptalk_studio.workbench.flow import WorkbenchFlow, WorkbenchFlowError
from deeptalk_studio.workbench.llm import (
    ChatCompletionsProvider,
    WorkbenchLLMError,
)
from deeptalk_studio.workbench.session import SessionStore
from deeptalk_studio.workbench.settings import (
    apply_settings_update,
    effective_chat_endpoint,
    is_configured,
    load_settings,
    masked_view,
    save_settings,
    settings_path,
    user_settings_path,
)

# ---- 测试凭据与会话数据安全（P0，review 5628439637 + 6366157284）-------
# pytest 与直接 `PYTHONPATH=src python3 -m unittest discover -s tests -v`
# （AGENTS.md/README.md 文档命令）都必须与真实 ~/.deeptalk 完全隔离：
# 绝不读取、覆盖或清除 Owner 已保存的 DeepSeek Key 与聊天历史。
#
# 本模块级兑底在本文件被任何 runner（pytest / unittest / IDE / CI）加载时
# 先于任何 settings/chat 读/写执行——用户级配置与聊天历史目录都指向
# 一次性临时目录，不解析真实 Path.home()；下方基类再为每个测试提供独立
# 目录，防止测试间串扰。生产运行不导入本文件，用户级 ~/.deeptalk 行为
# 保持不变。
import atexit as _atexit
import shutil as _shutil
import tempfile as _tempfile

from deeptalk_studio.workbench import settings as _settings_module
from deeptalk_studio.workbench import creative_chat as _creative_chat_module

if _settings_module.USER_SETTINGS_DIR is None:
    _SESSION_USER_DIR = Path(_tempfile.mkdtemp(prefix="deeptalk-tests-user-"))
    _atexit.register(_shutil.rmtree, _SESSION_USER_DIR, ignore_errors=True)
    _settings_module.USER_SETTINGS_DIR = _SESSION_USER_DIR
if _creative_chat_module.USER_CHAT_DIR is None:
    _SESSION_CHAT_DIR = Path(_tempfile.mkdtemp(prefix="deeptalk-tests-chat-"))
    _atexit.register(_shutil.rmtree, _SESSION_CHAT_DIR, ignore_errors=True)
    _creative_chat_module.USER_CHAT_DIR = _SESSION_CHAT_DIR


class _UserSettingsIsolatedTestCase(unittest.TestCase):
    """每个测试独享用户级配置与聊天历史目录（pytest 与 unittest 双入口均生效）。"""

    def setUp(self):
        super().setUp()
        settings_dir = Path(
            _tempfile.mkdtemp(prefix="deeptalk-user-%s-" % self.id()[:60])
        )
        self.addCleanup(_shutil.rmtree, settings_dir, ignore_errors=True)
        previous_settings = _settings_module.USER_SETTINGS_DIR
        _settings_module.USER_SETTINGS_DIR = settings_dir
        self.addCleanup(setattr, _settings_module, "USER_SETTINGS_DIR", previous_settings)
        chat_dir = Path(
            _tempfile.mkdtemp(prefix="deeptalk-chat-%s-" % self.id()[:60])
        )
        self.addCleanup(_shutil.rmtree, chat_dir, ignore_errors=True)
        previous_chat = _creative_chat_module.USER_CHAT_DIR
        _creative_chat_module.USER_CHAT_DIR = chat_dir
        self.addCleanup(setattr, _creative_chat_module, "USER_CHAT_DIR", previous_chat)

REPO = Path(__file__).resolve().parents[1]

SOURCE_A_TEXT = (
    "示例新闻社2026年10月20日报道，该市图书馆宣布自明年起将开放夜间阅览室，"
    "每周三和周五延长开放至二十三点，首年预算大约为一百二十万元。"
    "馆长说明夜间开放主要是为了服务备考学生和加班人群，馆方将与志愿者组织合作安排值班。"
    "报道同时提到，市财政局将在年度预算审核后决定是否续期。"
)
SOURCE_B_TEXT = (
    "市财政局官网2026年10月21日发布预算说明，2027年度公共文化支出拟增长百分之八，"
    "其中图书馆系统新增夜间开放专项经费一百二十万元，用于安保、照明与志愿服务补贴。"
    "说明同时指出，该专项经费为试点性质，有效期一年，期满后由市图书馆提交评估报告再定去留。"
)


def _research_payload():
    return {
        "topic": "本市图书馆夜间开放试点",
        "research_question": "夜间开放为谁服务，钱怎么花，谁来评估？",
        "scope_summary": "研究图书馆夜间开放试点的服务对象、预算来源和评估机制；不评价个人。",
        "executive_summary": "图书馆宣布夜间开放，预算一百二十万元，服务备考与加班人群；经费为一年试点，期满需评估续期。",
        "sources": [
            {
                "id": "S1",
                "title": "示例新闻社：图书馆明年起夜间开放",
                "url": "https://example.com/news/night-library",
                "publisher": "示例新闻社",
                "published_at": "2026-10-20",
                "accessed_at": "2026-10-21",
                "source_type": "media",
                "stance_summary": "报道开放计划、预算与服务对象。",
                "credibility_notes": "地方媒体报道，数字需与财政说明核对。",
                "independence_status": "independent",
                "syndication_of": "",
            },
            {
                "id": "S2",
                "title": "市财政局：2027年度公共文化支出预算说明",
                "url": "https://example.gov.cn/budget/2027-culture",
                "publisher": "示例市财政局",
                "published_at": "2026-10-21",
                "accessed_at": "2026-10-21",
                "source_type": "official",
                "stance_summary": "官方预算口径，说明专项经费性质。",
                "credibility_notes": "一手官方文件。",
                "independence_status": "independent",
                "syndication_of": "",
            },
        ],
        "claims": [
            {
                "id": "C1",
                "claim": "示例新闻社报道，图书馆明年起每周三、周五夜间开放至二十三点。",
                "classification": "media_report",
                "confidence": "high",
                "importance": "core",
                "risk_level": "medium",
                "risk_factors": ["attribution"],
                "notes": "保持报道归因。",
            },
            {
                "id": "C2",
                "claim": "市财政局说明，2027年新增图书馆夜间开放专项经费一百二十万元，为一年试点。",
                "classification": "confirmed_fact",
                "confidence": "high",
                "importance": "core",
                "risk_level": "low",
                "risk_factors": [],
                "notes": "官方预算口径。",
            },
            {
                "id": "C3",
                "claim": "据报道，馆方表示夜间开放主要服务备考学生和加班人群，并将与志愿者组织合作。",
                "classification": "party_statement",
                "confidence": "high",
                "importance": "key",
                "risk_level": "medium",
                "risk_factors": ["attribution"],
                "notes": "馆方说法，不是已验证成效。",
            },
        ],
        "evidence_links": [
            {
                "id": "E1",
                "claim_id": "C1",
                "source_id": "S1",
                "relation": "supports",
                "evidence_summary": "报道首段说明开放日与时间。",
                "evidence_locator": "报道第1段",
                "verification_notes": "",
            },
            {
                "id": "E2",
                "claim_id": "C2",
                "source_id": "S2",
                "relation": "supports",
                "evidence_summary": "预算说明列明专项经费金额与试点性质。",
                "evidence_locator": "说明第2段",
                "verification_notes": "",
            },
            {
                "id": "E3",
                "claim_id": "C3",
                "source_id": "S1",
                "relation": "attributes",
                "evidence_summary": "报道引述馆长说明服务对象与合作安排。",
                "evidence_locator": "报道第2段",
                "verification_notes": "",
            },
            {
                "id": "E4",
                "claim_id": "C2",
                "source_id": "S1",
                "relation": "supports",
                "evidence_summary": "媒体报道同样说明预算约一百二十万元，与官方口径互证。",
                "evidence_locator": "报道第1段",
                "verification_notes": "",
            },
        ],
        "timeline": [
            {
                "date": "2026-10-21",
                "event": "财政局发布预算说明；此前媒体报道开放计划。",
                "claim_ids": ["C1", "C2"],
                "evidence_link_ids": ["E1", "E2"],
            }
        ],
        "perspectives": [
            {
                "id": "P1",
                "actor": "图书馆",
                "position": "夜间开放服务特定人群。",
                "reasoning": "馆方说明服务对象。",
                "claim_ids": ["C3"],
                "evidence_link_ids": ["E3"],
                "category": "party",
            }
        ],
        "conflicts": [
            {
                "question": "试点一年后是否续期？",
                "side_a": "经费已列入预算。",
                "side_b": "试点性质，需评估报告决定去留。",
                "evidence_state": "预算说明明确一年试点与评估要求。",
                "claim_ids": ["C2"],
                "evidence_link_ids": ["E2"],
            }
        ],
        "open_questions": [
            {
                "question": "评估标准和报告由谁发布？",
                "why_it_matters": "决定续期判断依据。",
                "suggested_next_step": "关注图书馆后续公告。",
            }
        ],
        "angles": [
            {
                "title": "夜间图书馆：谁在用，谁买单，谁来评",
                "core_question": "一百二十万元买来的一年试点，该怎么判断值不值？",
                "why_now": "预算刚刚公开，试点明年启动。",
                "audience_value": "看清公共服务的目标、成本与评估链条。",
                "risks": "不评价个人，不预设续期结论。",
                "required_claim_ids": ["C1", "C2", "C3"],
            }
        ],
        "limitations": [
            "试点还未启动，成效数据不存在。",
            "报道与预算口径以两个独立来源核对，未逐字比对原文之外材料。",
        ],
        "handoff_to_script_agent": {
            "recommended_angle": "按“谁在用—谁买单—谁来评”讲清试点。",
            "central_tension": "便民愿望与一年期试点预算评估之间的张力。",
            "must_keep_claim_ids": [],
            "avoid_claims": ["不得声称夜间开放已证明有效或无效。"],
            "follow_up_research": ["追踪评估报告发布。"],
        },
    }


def _fact_check_payload(draft_report):
    checks = []
    for claim in draft_report["claims"]:
        quote_a = "每周三和周五延长开放至二十三点"
        quote_b = "图书馆系统新增夜间开放专项经费一百二十万元"
        source_id = "S2" if claim["id"] == "C2" else "S1"
        check = {
            "claim_id": claim["id"],
            "outcome": "verified",
            "original_classification": claim["classification"],
            "recommended_classification": claim["classification"],
            "searched_new_sources": False,
            "counterevidence_summary": "重抓来源原文未发现反向说法。",
            "source_ids": [source_id],
            "independence_assessment": "not_applicable",
            "verification_notes": (
                ("原文载明「" + quote_b + "」。" if source_id == "S2"
                 else "报道原文载明「" + quote_a + "」。")
                + "服务器逐字核对通过。"
            ),
        }
        checks.append(check)
    return {
        "artifact_version": "0.2",
        "review_id": "FC-wb-test",
        "report_id": draft_report["report_id"],
        "report_revision": draft_report["revision"],
        "created_at": "2026-10-21T12:00:00+08:00",
        "research_mode": "openai_api",
        "status": "completed",
        "tool_provenance": {
            "search_call_ids": ["webui-fetch-test"],
            "search_queries": [],
            "consulted_urls": ["https://example.com/news/night-library"],
            "citation_urls": [],
        },
        "queued_claim_ids": [],
        "new_sources": [],
        "evidence_links": [],
        "checks": checks,
        "overall_notes": "基于本地重抓来源原文逐字核对。",
    }


def _thesis_payload(report):
    claims = [claim["id"] for claim in report["claims"]]
    return {
        "core_question": "一百二十万元买来的一年夜间开放试点，该怎么判断值不值？",
        "one_sentence_answer": "先看清服务对象与预算性质，再等评估报告说话。",
        "core_thesis": "夜间开放是目标明确的便民试点，判断它要盯住谁在用、谁买单、谁来评，而不是提前下结论。",
        "counterintuitive_point": "预算列入不等于长期承诺，一年试点恰恰说明续期要靠评估说话。",
        "target_emotion": "好奇加务实，愿意追问公共服务账单。",
        "resonance": "观众关心公共服务的目标与成本，也想知道自己能不能用上。",
        "approval_point": "可以肯定便民初衷，也要指出评估标准尚不明确。",
        "comment_tension": "服务人群的合理性与试点边界的谨慎。",
        "spokesperson_value": "替观众追问钱怎么花、效果怎么算。",
        "value_identity": "讲证据、不预设立场，先看使用与评估。",
        "strongest_evidence_claim_ids": ["C2"],
        "counter_evidence_claim_ids": ["C1"],
        "uncertainty_limits": list(report["limitations"]),
        "crowded_angles": ["不做纯新闻播报，也不臆测续期结果。"],
        "differentiated_angle": "按“谁在用—谁买单—谁来评”三段式讲公共服务决策链。",
        "hook_promise": "从夜间图书馆的封面图进入，讲清一百二十万元买到什么。",
        "ending_question_or_judgment": "一年之后，评估报告会先问谁的问题？",
        "competitive_insight_notes": ["未参考任何创作者脚本，仅使用批准研究。"],
    }


def _thesis_review_payload(check_names):
    return {
        "checks": [
            {"check_name": name, "outcome": "pass", "reason": "逐项核对通过：" + name}
            for name in check_names
        ],
        "issues": [],
        "overall_summary": "选题与研究证据一致，无 blocking 问题。",
    }


def _script_payload(report):
    def beat(kind, purpose, narration, claims=(), evidence=(), basis=(), risk=""):
        return {
            "content_kind": kind,
            "purpose": purpose,
            "narration": narration,
            "claim_ids": list(claims),
            "evidence_link_ids": list(evidence),
            "analysis_basis_claim_ids": list(basis),
            "risk_notes": risk,
        }

    return {
        "working_title": "夜间图书馆：谁在用，谁买单，谁来评",
        "thesis": "夜间开放是目标明确的便民试点，判断它要盯住谁在用、谁买单、谁来评。",
        "audience_promise": "讲清一项公共服务的目标、成本与评估链条。",
        "beats": [
            beat(
                "question",
                "开场提出服务账单问题",
                "晚上十一点还亮着的图书馆，你上过吗？最近本市宣布，图书馆明年起每周三、周五夜间开放到二十三点。问题来了：这一晚的灯，要用多少钱，又该由谁来判断值不值？",
            ),
            beat(
                "attribution",
                "讲清开放安排",
                "先看事实。据示例新闻社报道，开放安排是每周三、周五两个晚上，时间是到二十三点，服务对象写得很清楚：备考的学生，和下了晚班的人。这是馆方通过媒体给出的正式说法。",
                claims=["C1"],
                evidence=["E1"],
            ),
            beat(
                "fact",
                "预算事实与试点性质",
                "再看钱。市财政局的预算说明写明白，二〇二七年新增图书馆夜间开放专项经费一百二十万元，用途包括安保、照明和志愿者补贴；同时注明性质是试点，有效期一年，期满要看评估报告再定去留。也就是说，钱是列进去的，但承诺只写到了一年。",
                claims=["C2"],
                evidence=["E2"],
            ),
            beat(
                "attribution",
                "馆方动机与合作方式",
                "馆长解释说，开放夜间阅览室，主要是给备考和加班的人一个去处，值班会和志愿者组织合作安排。注意，这是计划，不是已经跑了一年的成绩单，效果现在谁也不知道。",
                claims=["C3"],
                evidence=["E3"],
            ),
            beat(
                "analysis",
                "提出评估链问题",
                "所以真正值得盯的不是一百二十万这个数字，而是评估链条：一年之后，谁来统计有多少人来了？用什么标准判断值不值？评估报告会不会公开？这些问题不解决，支持者和反对者其实都在凭感觉站队。",
                basis=["C1", "C2", "C3"],
                risk="评论评估机制，不预设成效结论。",
            ),
            beat(
                "transition",
                "转入结尾",
                "公共服务最怕的不是花钱，是花钱之后没人说清楚花得值不值。",
            ),
        ],
        "closing": "明年这个时候，夜间图书馆会交出第一份评估报告。到时候你会看到数字：去了多少人、花了多少钱、值不值得续。在那之前，先别急着下结论，但可以从今天起盯着它。毕竟，这盏灯，用的是你我交的税。",
        "research_caveats": list(report["limitations"]),
        "research_gaps": [item["question"] for item in report["open_questions"]],
        "must_keep_omission_reasons": [],
    }


def _script_review_payload():
    return {
        "issues": [],
        "checks": [
            {"check_name": name, "outcome": "pass", "reason": "逐项核对通过：" + name}
            for name in SCRIPT_REVIEW_CHECK_NAMES
        ],
        "overall_notes": "稿件与研究证据一致，通过全部检查。",
    }


class FakeWorkbenchLLM:
    """Scripted provider: validates every fixture against the real schemas
    before handing it to the flow, exactly like a well-behaved provider."""

    provider_mode = "chat"

    def __init__(self, settings):
        self.settings = settings
        self._research = _research_payload()
        self._fact_check = None
        self._invented_url = False
        self.received_reference_insights = []

    def research(self, topic, research_question, sources, insights):
        self.received_reference_insights.append(list(insights or []))
        data = json.loads(json.dumps(self._research, ensure_ascii=False))
        if self._invented_url:
            data["sources"].append(
                {
                    "id": "S9",
                    "title": "模型编造来源",
                    "url": "https://example.org/invented",
                    "publisher": "无",
                    "published_at": "",
                    "accessed_at": "2026-10-21",
                    "source_type": "other",
                    "stance_summary": "无",
                    "credibility_notes": "模型凭记忆编造。",
                    "independence_status": "unknown",
                    "syndication_of": "",
                }
            )
        validate_json_schema(data, API_RESEARCH_DRAFT_JSON_SCHEMA, "api_research_draft")
        return ProviderResult(data=data, provenance=ProviderProvenance(search_calls=(), citations=()))

    def fact_check(self, report, sources):
        draft = report if isinstance(report, dict) else report.to_dict()
        data = _fact_check_payload(draft)
        validate_json_schema(data, FACT_CHECK_JSON_SCHEMA, "fact_check_artifact")
        return ProviderResult(data=data, provenance=ProviderProvenance(search_calls=(), citations=()))

    def write_thesis(self, report, narrative_insights=None):
        self.received_reference_insights.append(list(narrative_insights or []))
        data = _thesis_payload(report if isinstance(report, dict) else report.to_dict())
        validate_json_schema(data, THESIS_CONTENT_JSON_SCHEMA, "deep_talk_thesis_content")
        return ProviderResult(data=data, provenance=ProviderProvenance(search_calls=(), citations=()))

    def review_thesis(self, report, card_content, check_names):
        return ProviderResult(
            data=_thesis_review_payload(check_names),
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )

    def summarize_reference(self, transcript_text, metrics, metadata):
        return ProviderResult(
            data={
                "narrative_summary": "以问题开场，先事实后分析，结尾回扣。",
                "creator_viewpoint": (
                    "%s：先摆事实再鲜明评判的评论视角，关注事件本身与后续处理。"
                    % str(metadata.get("title", "测试参考"))[:40]
                ),
                "hook_style": "直接提问式钩子",
                "pacing": "中速，段间有停顿",
                "struct_patterns": ["问题—事实—评价", "结尾回扣"],
                "takeaways": ["开场30秒内给全信息量", "事实与分析分段"],
            },
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )

    def write_script(self, report, profile, target_duration_minutes, schema):
        if isinstance(report, dict) and "approved_research" in report:
            report = report["approved_research"]
        data = _script_payload(report if isinstance(report, dict) else report.to_dict())
        validate_json_schema(data, SCRIPT_DRAFT_CONTENT_JSON_SCHEMA, "deep_talk_script_draft")
        return ProviderResult(data=data, provenance=ProviderProvenance(search_calls=(), citations=()))

    def review_script(self, report, script, schema):
        return ProviderResult(
            data=_script_review_payload(),
            provenance=ProviderProvenance(search_calls=(), citations=()),
        )

    def ping(self):
        return


def _fake_fetcher(url):
    if url.startswith("https://example.com/news/night-library"):
        return {
            "ok": True,
            "url": url,
            "final_url": url,
            "title": "示例新闻社：图书馆明年起夜间开放",
            "text": SOURCE_A_TEXT,
            "bytes": len(SOURCE_A_TEXT),
            "sha256": "a" * 64,
            "fetched_at": "2026-10-21T12:00:00+08:00",
        }
    if url.startswith("https://example.gov.cn/budget/2027-culture"):
        return {
            "ok": True,
            "url": url,
            "final_url": url,
            "title": "市财政局：2027年度公共文化支出预算说明",
            "text": SOURCE_B_TEXT,
            "bytes": len(SOURCE_B_TEXT),
            "sha256": "b" * 64,
            "fetched_at": "2026-10-21T12:00:00+08:00",
        }
    return {"ok": False, "url": url, "error": "测试：不支持的地址"}


def _fake_discovery(topic, urls, count=3):
    return {
        "candidates": [
            {
                "bvid": "BV1test" + str(index),
                "url": "https://www.bilibili.com/video/BV1test%d" % index,
                "title": "测试参考视频 %d" % index,
                "uploader": "测试UP",
                "published_at": "2026-10-01T10:00:00+08:00",
                "view_count": 1000 * index,
                "view_count_status": "verified",
                "duration_sec": 60 + index,
                "user_supplied": False,
                "fetched_at": "2026-10-21T12:00:00+08:00",
            }
            for index in range(1, count + 1)
        ]
    }


def _fake_discovery_five(topic, urls):
    return _fake_discovery(topic, urls, count=5)


class _FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_acquirer(reference, downloads_dir, authorization_text, *, runner=None, timeout_seconds=900):
    record = {
        "bvid": reference["bvid"],
        "url": reference["url"],
        "title": reference.get("title", ""),
        "authorization_text": authorization_text,
        "authorized_at": "2026-10-21T12:00:00+08:00",
        "media_path": "",
        "media_bytes": 1024,
        "media_sha256": "c" * 64,
        "duration_seconds": 120,
        "tool": "fixture",
        "status": "downloaded",
    }
    return record


class SettingsTests(_UserSettingsIsolatedTestCase):
    def test_deepseek_preset_uses_official_defaults_and_single_endpoint_suffix(self):
        data = apply_settings_update(load_settings(Path(tempfile.mkdtemp())), {
            "provider_mode": "deepseek",
        })
        self.assertEqual(data["chat_base_url"], "https://api.deepseek.com")
        self.assertEqual(data["model"], "deepseek-flash")
        self.assertEqual(
            effective_chat_endpoint(data),
            "https://api.deepseek.com/chat/completions",
        )
        already_endpoint = dict(data, chat_base_url="https://api.deepseek.com/chat/completions")
        self.assertEqual(
            effective_chat_endpoint(already_endpoint),
            "https://api.deepseek.com/chat/completions",
        )

    def test_deepseek_switch_preserves_key_download_folder_and_connection_observation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data = apply_settings_update(load_settings(root), {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "custom-model",
                "api_key": "sk-preserve-me",
                "downloads_dir": raw,
            })
            data["connection_status"] = "passed"
            data["connection_kind"] = "real"
            save_settings(root, data)
            switched = apply_settings_update(load_settings(root), {"provider_mode": "deepseek"})
            self.assertEqual(switched["api_key"], "sk-preserve-me")
            self.assertEqual(switched["downloads_dir"], raw)
            self.assertEqual(switched["connection_status"], "not_tested")
            self.assertEqual(switched["model"], "deepseek-flash")

    def test_deepseek_mode_discards_stale_custom_endpoint_and_model(self):
        """Nexus P0（PR #45 review 5625537364）：切换到 DeepSeek 预设后，
        服务端无条件强制官方端点与官方模型，丢弃残留的自定义值；
        显式提交的旧 Chat 端点/模型名同样被覆盖，绝不把新粘贴的
        DeepSeek Key 路由到先前的自定义端点。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "custom-model",
                "api_key": "sk-old",
            }))
            # 切换 payload 不带端点/模型：残留 custom 值必须被丢弃
            switched = apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
                "api_key": "sk-newly-pasted",
            })
            self.assertEqual(switched["chat_base_url"], "https://api.deepseek.com")
            self.assertEqual(switched["model"], "deepseek-flash")
            self.assertEqual(switched["api_key"], "sk-newly-pasted")
            # 即使 payload 显式带上旧/自定义端点，deepseek 模式仍强制官方值
            hostile = apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
                "chat_base_url": "http://127.0.0.1:8931/v1",
                "model": "attacker-model",
            })
            self.assertEqual(hostile["chat_base_url"], "https://api.deepseek.com")
            self.assertEqual(hostile["model"], "deepseek-flash")
            # 凭证路由终点必须是官方 chat/completions 端点
            self.assertEqual(
                effective_chat_endpoint(hostile),
                "https://api.deepseek.com/chat/completions",
            )

    def test_connection_status_view_is_masked_and_clear_is_explicit(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data = apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
                "api_key": "sk-secret-123456",
            })
            data["connection_status"] = "failed"
            data["connection_kind"] = "real"
            data["connection_error"] = "HTTP 401：请检查 API Key"
            save_settings(root, data)
            view = masked_view(load_settings(root))
            self.assertEqual(view["connection_status"], "failed")
            self.assertEqual(view["connection_kind"], "real")
            self.assertNotIn("sk-secret", json.dumps(view))
            cleared = apply_settings_update(load_settings(root), {"api_key": ""})
            self.assertEqual(cleared["api_key"], "")
            self.assertFalse(is_configured(cleared))

    def test_chat_provider_maps_http_failure_without_disclosing_key(self):
        from urllib.error import HTTPError

        secret = "sk-never-return-this"

        def transport(url, headers, body, timeout):
            raise HTTPError(url, 401, "unauthorized", {}, None)

        provider = ChatCompletionsProvider(
            secret, "deepseek-flash", "https://api.deepseek.com", transport=transport
        )
        with self.assertRaises(WorkbenchLLMError) as ctx:
            provider.ping()
        self.assertEqual(ctx.exception.http_status, 401)
        self.assertEqual(ctx.exception.category, "unauthorized")
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn(secret, str(ctx.exception))

    def test_chat_provider_maps_timeout_as_actionable_error(self):
        def transport(url, headers, body, timeout):
            raise TimeoutError("timed out")

        provider = ChatCompletionsProvider(
            "sk-timeout", "deepseek-flash", "https://api.deepseek.com", transport=transport
        )
        with self.assertRaises(WorkbenchLLMError) as ctx:
            provider.ping()
        self.assertEqual(ctx.exception.category, "timeout")
        self.assertIn("超时", str(ctx.exception))

    def test_settings_roundtrip_mask_and_partial_key_update(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "chat",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "test-model",
                "api_key": "sk-very-long-test-key-1234",
                "downloads_dir": str(Path(raw).resolve()),
            }))
            data = load_settings(root)
            self.assertTrue(is_configured(data))
            view = masked_view(data)
            self.assertNotIn("sk-very-long", json.dumps(view))
            self.assertIn("…", view["api_key_masked"])
            # omitted key keeps the old key; empty string clears it
            updated = apply_settings_update(data, {"model": "another"})
            self.assertEqual(updated["api_key"], data["api_key"])
            cleared = apply_settings_update(updated, {"api_key": ""})
            self.assertEqual(cleared["api_key"], "")
            self.assertFalse(is_configured(cleared))

    def test_saved_key_is_shared_across_worktrees_and_survives_updates(self):
        """Owner Key 持久化（issuecomment-6364369899）：一次保存后，
        不同工作树 root / 产品更新加载同一份用户级配置，绝不要求
        Owner 重新输入 Key；仓库级 config 不再被写入。"""
        with tempfile.TemporaryDirectory() as raw_a, tempfile.TemporaryDirectory() as raw_b:
            root_a = Path(raw_a)
            root_b = Path(raw_b)
            save_settings(root_a, apply_settings_update(load_settings(root_a), {
                "provider_mode": "deepseek",
                "api_key": "sk-owner-shared-key-9876abcd",
            }))
            # 另一个工作树（不同 root）加载同一份已保存 Key
            shared = load_settings(root_b)
            self.assertEqual(shared["api_key"], "sk-owner-shared-key-9876abcd")
            self.assertEqual(shared["provider_mode"], "deepseek")
            # 「产品更新」视角：新 root 上继续修改，旧 root 也能读到新值
            save_settings(root_b, apply_settings_update(load_settings(root_b), {
                "model": "deepseek-flash",
            }))
            reloaded = load_settings(root_a)
            self.assertEqual(reloaded["api_key"], "sk-owner-shared-key-9876abcd")
            self.assertEqual(reloaded["model"], "deepseek-flash")
            # 仓库级 config 不再被写入（用户级是唯一真源）
            self.assertFalse(settings_path(root_a).exists())
            self.assertFalse(settings_path(root_b).exists())

    def test_repo_settings_migrate_once_to_user_level_and_stay_0600(self):
        """向后兼容迁移：已有仓库级配置在首次加载时一次性复制到用户级
        （0600），原文件保留（旧版本 fallback）；显式清除 Key 时同步
        清掉仓库级旧 Key，不复活、不残留明文。"""
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as raw_b:
            root = Path(raw)
            repo_cfg = settings_path(root)
            repo_cfg.parent.mkdir(parents=True, exist_ok=True)
            repo_cfg.write_text(json.dumps({
                "provider_mode": "deepseek",
                "api_key": "sk-migrate-me-998877",
                "model": "deepseek-flash",
            }, ensure_ascii=False), encoding="utf-8")
            data = load_settings(root)  # 首次加载触发迁移
            self.assertEqual(data["api_key"], "sk-migrate-me-998877")
            user_path = user_settings_path()
            self.assertTrue(user_path.is_file())
            self.assertEqual(user_path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(repo_cfg.is_file())  # 原文件保留（旧版本 fallback）
            # 用户级成为唯一真源：另一工作树直接读到迁移结果
            self.assertEqual(load_settings(Path(raw_b))["api_key"], "sk-migrate-me-998877")
            # 显式清除 Key：用户级与仓库级旧 Key 一起清掉
            save_settings(root, apply_settings_update(load_settings(root), {"api_key": ""}))
            self.assertEqual(load_settings(root)["api_key"], "")
            self.assertEqual(json.loads(repo_cfg.read_text(encoding="utf-8"))["api_key"], "")

    def test_settings_rejects_nonexistent_downloads_dir(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(Exception):
                apply_settings_update(load_settings(root), {
                    "downloads_dir": "/definitely/not/existing/dir/xyz",
                })

    def test_settings_rejects_non_writable_save_folder(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with mock.patch.object(_settings_module.os, "access", return_value=False):
                with self.assertRaisesRegex(Exception, "不可写"):
                    apply_settings_update(load_settings(root), {"downloads_dir": raw})

    def test_save_folder_update_preserves_saved_api_key(self):
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as settings_root:
            previous = _settings_module.USER_SETTINGS_DIR
            _settings_module.USER_SETTINGS_DIR = Path(settings_root)
            self.addCleanup(setattr, _settings_module, "USER_SETTINGS_DIR", previous)
            root = Path(raw)
            configured = apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek", "api_key": "sk-keep-save-folder-test"
            })
            save_settings(root, configured)
            updated = apply_settings_update(load_settings(root), {"downloads_dir": raw})
            save_settings(root, updated)
            self.assertEqual(load_settings(root)["api_key"], "sk-keep-save-folder-test")
            self.assertEqual(masked_view(load_settings(root))["downloads_dir"], raw)

    def test_native_folder_picker_is_shell_free_and_handles_cancel(self):
        chooser = getattr(_settings_module, "choose_local_directory", None)
        self.assertTrue(callable(chooser), "settings should expose a native folder chooser")
        with tempfile.TemporaryDirectory() as raw:
            selected = str(Path(raw) / "")
            with mock.patch.object(_settings_module.platform, "system", return_value="Darwin"), \
                 mock.patch.object(_settings_module.subprocess, "run", return_value=subprocess.CompletedProcess(
                     ["osascript"], 0, stdout=selected + "\n", stderr=""
                 )) as run:
                result = chooser()
            self.assertEqual(result, {"path": selected, "cancelled": False})
            self.assertEqual(run.call_args.args[0][:2], ["osascript", "-e"])
            self.assertNotIn("shell", run.call_args.kwargs)
            with mock.patch.object(_settings_module.platform, "system", return_value="Darwin"), \
                 mock.patch.object(_settings_module.subprocess, "run", return_value=subprocess.CompletedProcess(
                     ["osascript"], 1, stdout="", stderr="execution error: User canceled. (-128)"
                 )):
                self.assertEqual(chooser(), {"path": "", "cancelled": True})

    def test_native_folder_picker_explains_unsupported_platform(self):
        chooser = getattr(_settings_module, "choose_local_directory", None)
        self.assertTrue(callable(chooser), "settings should expose a native folder chooser")
        with mock.patch.object(_settings_module.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(Exception, "填写绝对路径"):
                chooser()

    def test_test_settings_without_key_persists_waiting_status(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow = WorkbenchFlow(root, provider_factory=lambda settings: None)
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.test_settings()
            # Issue #44 settings UX: the user-facing message must be natural
            # Chinese naming what is missing — never the internal status code.
            message = str(ctx.exception)
            self.assertIn("设置尚未完成", message)
            self.assertIn("API Key", message)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", message)
            view = flow.get_settings()
            self.assertEqual(view["connection_status"], "waiting_for_api_key")
            self.assertEqual(view["connection_kind"], "fixture")

    def test_test_settings_persists_fixture_success_without_secret(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            class Provider:
                def ping(self):
                    return None

            flow = WorkbenchFlow(root, provider_factory=lambda settings: Provider())
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
                "api_key": "sk-private-fixture",
            }))
            result = flow.test_settings()
            self.assertEqual(result["status"], "passed")
            # Issue #44 settings UX: a fixture connection must carry its kind
            # so the UI can render a dev-test state instead of real success.
            self.assertEqual(result["connection_kind"], "fixture")
            view = flow.get_settings()
            self.assertEqual(view["connection_status"], "passed")
            self.assertNotIn("sk-private-fixture", json.dumps(view))

    def test_test_settings_missing_field_message_names_each_gap_in_chinese(self):
        """Issue #44 settings UX: the not-configured message lists the exact
        missing pieces in natural Chinese (key / model / address) depending
        on the provider mode, with no internal status codes."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow = WorkbenchFlow(root, provider_factory=lambda settings: None)
            # DeepSeek preset after a keyless save: model + address are
            # auto-configured, so only the API Key should be named.
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
            }))
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.test_settings()
            message = str(ctx.exception)
            self.assertIn("API Key", message)
            self.assertNotIn("模型名称", message)
            self.assertNotIn("API 地址", message)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", message)
            # A chat config missing only the model names the model in the
            # message (an empty chat URL cannot be saved at all).
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "chat",
                "api_key": "sk-test-half-configured",
                "chat_base_url": "https://llm.example.com/v1",
                "model": "",
            }))
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.test_settings()
            message = str(ctx.exception)
            self.assertIn("模型名称", message)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", message)

    def test_deepseek_tools_gate_message_is_friendly_without_codes(self):
        """Issue #44 settings UX: the DeepSeek Search/Fetch gate reports the
        missing fields in natural Chinese, not WAITING_FOR_OWNER_API_KEY."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow = WorkbenchFlow(root, provider_factory=lambda settings: None)
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
            }))
            session = flow.store.create("本市图书馆夜间开放试点", [], None)
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.search_deepseek(
                    session["session_id"], "预算", opt_in=True, max_requests=2
                )
            message = str(ctx.exception)
            self.assertIn("设置尚未完成", message)
            self.assertIn("API Key", message)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", message)


class AcquisitionTests(_UserSettingsIsolatedTestCase):
    def test_authorize_requires_meaningful_attestation(self):
        for bad in ["", "同意", "我同意在本地研究使用这些视频"]:
            with self.assertRaises(acquisition.WorkbenchAcquisitionError):
                acquisition.authorize(bad)
        self.assertIn("授权", acquisition.authorize("我授权在本地使用该参考视频做研究分析。"))

    def test_acquire_fails_closed_on_platform_denial(self):
        def deny_runner(command, **kwargs):
            return _FakeCompleted(
                returncode=1,
                stderr="ERROR: [cookies] HTTP Error 412: Precondition Failed — risk control",
            )

        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(acquisition.WorkbenchAcquisitionError) as ctx:
                acquisition.acquire_reference(
                    {"bvid": "BV1x", "url": "https://www.bilibili.com/video/BV1x", "title": "t"},
                    Path(raw),
                    "我授权在本地研究使用该参考视频。",
                    runner=deny_runner,
                )
            self.assertIn("不绕过", str(ctx.exception))

    def test_metrics_and_transcript_parsing(self):
        transcript = {
            "text": "第一段文本内容。第二段是问题句吗？第三段包含数字123。",
            "segments": [
                {"start_seconds": 0.0, "end_seconds": 5.0, "text": "第一段文本内容。"},
                {"start_seconds": 5.2, "end_seconds": 10.0, "text": "第二段是问题句吗？"},
                {"start_seconds": 10.2, "end_seconds": 15.0, "text": "第三段包含数字123。"},
            ],
        }
        metrics = acquisition.analyze_transcript(
            transcript, {"title": "t", "bvid": "BV1x", "view_count": 12, "duration_sec": 0}
        )
        self.assertEqual(metrics["segment_count"], 3)
        self.assertEqual(metrics["question_count"], 1)
        self.assertEqual(metrics["duration_seconds"], 15.0)
        self.assertTrue(metrics["top_terms"])


class SessionStoreTests(_UserSettingsIsolatedTestCase):
    def test_create_load_update_and_latest(self):
        with tempfile.TemporaryDirectory() as raw:
            store = SessionStore(Path(raw))
            session = store.create("主题", [{"bvid": "BV1"}], None)
            loaded = store.load(session["session_id"])
            self.assertEqual(loaded["topic"], "主题")

            def mutate(data):
                data["status"] = "research"

            updated = store.update(session["session_id"], mutate)
            self.assertEqual(updated["status"], "research")
            self.assertEqual(store.load_latest()["session_id"], session["session_id"])


class DeepSeekWorkbenchTests(_UserSettingsIsolatedTestCase):
    """Issue #36: explicit, capped DeepSeek Search/Fetch stays offline in tests."""

    class Client:
        def __init__(self):
            self.calls = []

        def search(self, query, count=5, need_content=False):
            self.calls.append(("search", query, count, need_content))
            return {
                "request_id": "req-search-fixture",
                "results": [
                    {
                        "title": "官方公告",
                        "url": "https://example.gov/notice",
                        "content": "公告正文摘要",
                        "published_at": "2026-10-21",
                    }
                ],
            }

        def fetch(self, url):
            self.calls.append(("fetch", url))
            return {
                "request_id": "req-fetch-fixture",
                "url": url,
                "title": "官方公告",
                "content": "这是可供独立核验的原文正文，包含足够长的事实材料。",
                "published_at": "2026-10-21",
            }

    def _flow(self, root, client):
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery,
            provider_factory=lambda settings: FakeWorkbenchLLM(settings),
            deepseek_client_factory=lambda settings: client,
        )

    @staticmethod
    def _configure(root):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "deepseek",
            "api_key": "sk-offline-fixture-only",
        }))

    def test_search_requires_explicit_opt_in_without_spending_or_calling_client(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            client = self.Client()
            self._configure(root)
            flow = self._flow(root, client)
            sid = flow.start_session("本市图书馆夜间开放试点", [])["session_id"]
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.search_deepseek(sid, "预算证据", opt_in=False, max_requests=2)
            self.assertIn("明确勾选", str(ctx.exception))
            self.assertEqual(client.calls, [])
            self.assertEqual(flow.store.load(sid)["search_budget"]["used"], 0)

    def test_search_and_fetch_consume_cap_and_persist_source_provenance(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            client = self.Client()
            self._configure(root)
            flow = self._flow(root, client)
            sid = flow.start_session("本市图书馆夜间开放试点", [])["session_id"]
            searched = flow.search_deepseek(
                sid, "预算证据", opt_in=True, max_requests=2, count=3, need_content=True
            )
            self.assertEqual(searched["results"][0]["url"], "https://example.gov/notice")
            self.assertEqual(searched["search_budget"]["used"], 1)
            self.assertEqual(client.calls[0], ("search", "预算证据", 3, True))
            fetched = flow.fetch_deepseek_source(
                sid, "https://example.gov/notice", opt_in=True, max_requests=2
            )
            self.assertEqual(fetched["kind"], "deepseek_fetched")
            self.assertEqual(fetched["request_id"], "req-fetch-fixture")
            self.assertEqual(fetched["search_budget"]["used"], 2)
            source_path = flow.store.sources_dir(sid) / "S1.json"
            source = flow.store.load_json(source_path)
            self.assertEqual(source["kind"], "deepseek_fetched")
            self.assertEqual(source["request_id"], "req-fetch-fixture")
            self.assertEqual(source["provenance_method"], "deepseek_fetch")
            self.assertEqual(len(source["sha256"]), 64)
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.search_deepseek(sid, "再次检索", opt_in=True, max_requests=2)
            self.assertIn("上限", str(ctx.exception))
            self.assertEqual(len(client.calls), 2)
            view = flow.view(sid)
            self.assertEqual(view["search_budget"]["used"], 2)
            self.assertEqual(view["sources"][0]["kind"], "deepseek_fetched")
            self.assertEqual(view["sources"][0]["request_id"], "req-fetch-fixture")
            self.assertEqual(view["sources"][0]["provenance_method"], "deepseek_fetch")

    def test_missing_deepseek_key_is_truthful_and_never_constructs_client(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self_calls = []
            flow = WorkbenchFlow(
                root,
                discovery_runner=_fake_discovery,
                deepseek_client_factory=lambda settings: self_calls.append(settings),
            )
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
            }))
            sid = flow.start_session("本市图书馆夜间开放试点", [])["session_id"]
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.search_deepseek(sid, "证据", opt_in=True, max_requests=1)
            # Issue #44 settings UX: fail-closed behavior unchanged; the
            # message is natural Chinese with no internal status code.
            message = str(ctx.exception)
            self.assertIn("设置尚未完成", message)
            self.assertIn("API Key", message)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", message)
            self.assertEqual(self_calls, [])
            self.assertEqual(flow.store.load(sid)["search_budget"]["used"], 0)


class AudioWorkbenchTests(_UserSettingsIsolatedTestCase):
    """Issue #37: safe import/status around the canonical audio delivery core."""

    @staticmethod
    def _flow(root, runner=None, limit=None):
        kwargs = {}
        if runner is not None:
            kwargs["audio_delivery_runner"] = runner
        if limit is not None:
            kwargs["audio_upload_limit_bytes"] = limit
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery,
            provider_factory=lambda settings: FakeWorkbenchLLM(settings),
            **kwargs,
        )

    def test_import_audio_is_bounded_atomic_and_origin_persisted(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow = self._flow(root, limit=4)
            sid = flow.start_session("本市图书馆夜间开放试点", [])["session_id"]
            imported = flow.import_audio(sid, "take.wav", io.BytesIO(b"abcd"), "owner_made")
            self.assertEqual(imported["origin"], "owner_made")
            self.assertEqual(imported["byte_size"], 4)
            self.assertEqual(imported["sha256"], hashlib.sha256(b"abcd").hexdigest())
            self.assertTrue(Path(imported["path"]).is_file())
            view = flow.view(sid)
            self.assertEqual(view["audio"]["filename"], "take.wav")
            self.assertEqual(view["audio"]["origin"], "owner_made")
            with self.assertRaises(WorkbenchFlowError):
                flow.import_audio(sid, "../escape.wav", io.BytesIO(b"x"), "owner_made")
            with self.assertRaises(WorkbenchFlowError):
                flow.import_audio(sid, "take.exe", io.BytesIO(b"x"), "owner_made")
            with self.assertRaises(WorkbenchFlowError):
                flow.import_audio(sid, "too-big.wav", io.BytesIO(b"12345"), "owner_made")
            with self.assertRaises(WorkbenchFlowError):
                flow.import_audio(sid, "empty.wav", io.BytesIO(b""), "owner_made")
            with self.assertRaises(WorkbenchFlowError):
                flow.import_audio(sid, "other.wav", io.BytesIO(b"x"), "unverified")
            self.assertFalse((flow.store.session_dir(sid) / "too-big.wav").exists())

    def test_delivery_without_reviewed_material_is_typed_waiting_for_owner_review(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow = self._flow(root)
            sid = flow.start_session("本市图书馆夜间开放试点", [])["session_id"]
            flow.import_audio(sid, "take.wav", io.BytesIO(b"audio"), "external_voice_authorized")
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.run_audio_delivery(sid)
            self.assertIn("WAITING_FOR_OWNER_REVIEW", str(ctx.exception))
            state = flow.view(sid)
            self.assertEqual(state["audio_delivery"]["status"], "waiting_for_owner_review")
            self.assertNotIn("finished_cut_path", state["audio_delivery"])

    def test_injected_delivery_exposes_timeline_gaps_and_edit_map_without_fake_preview(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def runner(session_root, repo_root):
                return {
                    "delivery": {
                        "timeline": {"spans": [{"span_id": "ST001", "start_seconds": "0", "end_seconds": "1"}]},
                        "gaps": [{"span_id": "ST001", "reason": "AUDIO_ONLY", "detail": "需要人工补画面"}],
                    },
                    "asset_pack": {"machine_map": {"rows": [{"decision": "AUDIO_ONLY"}]}},
                    "qa": {"package_gate_status": "warnings"},
                    "paths": {"markdown": Path(session_root) / "DeepTalk-Aligned-Edit" / "edit-map.md",
                              "json": Path(session_root) / "DeepTalk-Aligned-Edit" / "edit-map.json",
                              "manifest": Path(session_root) / "DeepTalk-Aligned-Edit" / "manifest.json",
                              "qa": Path(session_root) / "DeepTalk-Aligned-Edit" / "qa.json"},
                    "preview_path": None,
                }

            flow = self._flow(root, runner=runner)
            sid = flow.start_session("本市图书馆夜间开放试点", [])["session_id"]
            flow.import_audio(sid, "take.wav", io.BytesIO(b"audio"), "owner_made")
            result = flow.run_audio_delivery(sid)
            self.assertEqual(result["status"], "delivered")
            self.assertEqual(result["timeline_count"], 1)
            self.assertEqual(result["gap_count"], 1)
            state = flow.view(sid)
            self.assertEqual(state["audio_delivery"]["status"], "delivered")
            self.assertEqual(state["audio_delivery"]["timeline"][0]["span_id"], "ST001")
            self.assertEqual(state["audio_delivery"]["gaps"][0]["reason"], "AUDIO_ONLY")
            self.assertFalse(state["audio_delivery"].get("preview_path"))

class FullLoopTests(_UserSettingsIsolatedTestCase):
    """Ordinary-user acceptance path, engine-real, LLM scripted."""

    def _flow(self, root: Path, provider=None):
        provider = provider or FakeWorkbenchLLM
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery,
            provider_factory=lambda settings: provider(settings)
            if isinstance(provider, type)
            else provider,
            fetcher=_fake_fetcher,
            acquire_runner=None,
            audio_runner=None,
            whisper_runner=None,
        )

    def _configure(self, root: Path):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "chat",
            "chat_base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "api_key": "sk-test-key",
            "downloads_dir": str(root.resolve()),  # any existing dir
        }))

    def test_acquire_references_persists_state_real_flow_path(self):
        """Issue #23 E2E regression: the REAL flow.acquire_references body
        must persist each successful download into session.json.

        The first browser E2E crashed here with ``unhashable type: 'dict'``
        because the _mark callback did not honor SessionStore.update's
        ``mutate(session)`` protocol (session dict passed positionally).
        """
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            bvid = view["references"][0]["bvid"]
            media = Path(root) / "ref-real.mp4"
            media.write_bytes(b"fixture-media-bytes")

            def acquirer(reference, downloads_dir, authorization_text, *, runner=None, timeout_seconds=900):
                record = _fake_acquirer(reference, downloads_dir, authorization_text)
                record["media_path"] = str(media)
                return record

            with mock.patch.object(acquisition, "acquire_reference", acquirer):
                result = flow.acquire_references(sid, [bvid], "我授权在本地研究使用该参考视频。")
            self.assertTrue(result["results"][0]["ok"], result)
            persisted = flow.store.load(sid)["references"][bvid]
            self.assertEqual(persisted["status"], "downloaded")
            self.assertEqual(persisted["media_path"], str(media))
            self.assertEqual(persisted["title"], view["references"][0]["title"])
            self.assertTrue((flow.store.references_dir(sid) / bvid / "acquisition.json").is_file())

            # Idempotent re-run: an existing download with the file on disk is
            # skipped, never downloaded (or archived) again.
            with mock.patch.object(
                acquisition, "acquire_reference", wraps=acquirer
            ) as patched:
                again = flow.acquire_references(sid, [bvid], "我授权再次声明使用该参考视频。")
            patched.assert_not_called()
            self.assertTrue(again["results"][0]["ok"], again)
            self.assertEqual(again["results"][0].get("skipped"), "already_downloaded")

    def test_analyze_reference_persists_state_real_flow_path(self):
        """Issue #23 E2E regression: the REAL flow.analyze_reference body
        must persist the analyzed status into session.json (same
        ``mutate(session)`` protocol as acquire)."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            bvid = view["references"][0]["bvid"]
            media = Path(root) / "ref-analyze.mp4"
            media.write_bytes(b"fixture-media-bytes")

            def acquirer(reference, downloads_dir, authorization_text, *, runner=None, timeout_seconds=900):
                record = _fake_acquirer(reference, downloads_dir, authorization_text)
                record["media_path"] = str(media)
                return record

            def audio_runner(command, **kwargs):
                wav_path = Path(command[-1])
                wav_path.write_bytes(b"RIFF" + b"\x00" * 100)
                return _FakeCompleted(returncode=0)

            def whisper_runner(command, **kwargs):
                base = Path(command[command.index("--output-file") + 1])
                base.with_suffix(".json").write_text(json.dumps({
                    "transcription": [
                        {"offset": 0, "duration": 6000, "text": "问题开场钩子测试。"},
                        {"offset": 6200, "duration": 5000, "text": "先事实后分析。"},
                    ],
                    "result": {"language": "zh"},
                }, ensure_ascii=False), encoding="utf-8")
                return _FakeCompleted(returncode=0)

            class _Installation:
                runtime_path = "/usr/bin/true"
                model_path = "/models/large-v3.bin"
                dtw_preset = "none"
                model_name = "large-v3"
                runtime_version = "fixture"

            class _Bootstrap:
                def ensure(self):
                    return _Installation()

            flow.audio_runner = audio_runner
            flow.whisper_runner = whisper_runner
            flow.whisper_bootstrap = _Bootstrap()
            with mock.patch.object(acquisition, "acquire_reference", acquirer):
                flow.acquire_references(sid, [bvid], "我授权在本地研究使用该参考视频。")
                result = flow.analyze_reference(sid, bvid)
            self.assertEqual(result["bvid"], bvid)
            self.assertTrue(result["study"]["narrative_summary"])
            persisted = flow.store.load(sid)["references"][bvid]
            self.assertEqual(persisted["status"], "analyzed")
            self.assertTrue(Path(persisted["study_path"]).is_file())
            self.assertEqual(persisted["media_path"], str(media))

    def test_full_loop_topic_to_reviewed_script(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            # 1. start session (discovery reused, 3 candidates)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            self.assertEqual(len(view["references"]), 3)

            # 2. reference analysis with fixture runners (authorized)
            with mock.patch.object(
                acquisition, "acquire_reference", _fake_acquirer
            ), mock.patch.object(
                flow, "analyze_reference", None, create=True
            ):
                record = _fake_acquirer(
                    view["references"][0], Path(root), "我授权在本地研究使用该参考视频。"
                )
                media = Path(root) / "ref.mp4"
                media.write_bytes(b"fixture-media-bytes")
                record["media_path"] = str(media)
                flow.store.update(sid, lambda s: s["references"].update({
                    view["references"][0]["bvid"]: {
                        "status": "downloaded",
                        "media_path": str(media),
                        "title": view["references"][0]["title"],
                        "url": view["references"][0]["url"],
                        "view_count": view["references"][0]["view_count"],
                        "view_count_status": "verified",
                        "duration_sec": view["references"][0]["duration_sec"],
                    }
                }))

                def fake_analyze(session_id, bvid):
                    transcript = {
                        "text": "问题开场钩子测试，先抛出一个观众关心的问题，然后用事实回答。",
                        "segments": [
                            {"start_seconds": 0.0, "end_seconds": 6.0, "text": "问题开场钩子测试，"},
                            {"start_seconds": 6.2, "end_seconds": 12.0, "text": "先抛出一个观众关心的问题，然后用事实回答。"},
                        ],
                    }
                    ref_dir = flow.store.references_dir(session_id) / bvid
                    ref_dir.mkdir(parents=True, exist_ok=True)
                    (ref_dir / "transcript.json").write_text(
                        json.dumps(transcript, ensure_ascii=False), encoding="utf-8"
                    )
                    metrics = acquisition.analyze_transcript(
                        transcript, flow.store.load(session_id)["references"][bvid]
                    )
                    study = dict(metrics)
                    study.update(FakeWorkbenchLLM({}).summarize_reference("", metrics, {}).data)
                    study["media_path"] = str(media)
                    path = ref_dir / "study.json"
                    path.write_text(json.dumps(study, ensure_ascii=False), encoding="utf-8")
                    flow.store.update(session_id, lambda s: (
                        s["references"][bvid].update({"status": "analyzed", "study_path": str(path)})
                    ))
                    return {"bvid": bvid, "study": study}

                flow.analyze_reference = fake_analyze
                flow.analyze_reference(sid, view["references"][0]["bvid"])

            state = flow.view(sid)
            study = state["references"][0]["study"]
            self.assertTrue(study["narrative_summary"])
            self.assertTrue(study["top_terms"])

            # 3. sources (one fetched, one pasted with URL)
            flow.add_source_url(sid, "https://example.com/news/night-library")
            flow.add_source_text(
                sid, "市财政局预算说明", SOURCE_B_TEXT, "https://example.gov.cn/budget/2027-culture"
            )

            # 3a. chat mode must reject invented sources
            provider = FakeWorkbenchLLM({})
            provider._invented_url = True
            strict_flow = self._flow(root, provider=provider)
            with self.assertRaises(WorkbenchFlowError) as ctx:
                strict_flow.generate_research(sid, "")
            self.assertIn("未提供的来源", str(ctx.exception))

            # 4. research draft (real engine save under tmp reports/)
            result = flow.generate_research(sid, "夜间开放为谁服务？")
            self.assertEqual(result["status"], "fact_check_pending")
            self.assertTrue(Path(result["draft_path"]).is_file())

            # 5. real fact check passes the quality gate
            fc = flow.run_fact_check(sid)
            self.assertEqual(fc["status"], "reviewed", fc.get("gate_reasons"))
            self.assertEqual(fc["quote_downgraded_checks"], 0)
            self.assertEqual(fc["gate_status"], "pass")

            # 6. approval → ready_for_script
            approval = flow.approve_research(sid, "我确认研究结论，批准进入写稿。")
            self.assertTrue(approval["ready_for_script"])

            # 7. thesis → gate review → human approval
            thesis = flow.generate_thesis(sid)
            self.assertEqual(thesis["status"], "draft")
            review = flow.review_thesis(sid)
            self.assertEqual(review["gate_decision"], "pass")
            confirmed = flow.approve_thesis(
                sid, "我确认本期内容方向与选题卡一致，确认进入写稿。"
            )
            self.assertEqual(confirmed["status"], "approved_for_script")

            # 8. script + review
            script = flow.generate_script(sid)
            self.assertEqual(script["status"], "reviewed", script)
            self.assertEqual(script["gate_status"], "pass")
            self.assertIn("夜间图书馆", script["teleprompter_text"])

            # 9. final view
            final = flow.final_script(sid)
            self.assertTrue(final["teleprompter_text"])
            self.assertTrue(Path(final["teleprompter_path"]).is_file())

            # canonical engine trees really hold the artifacts
            reports = list((root / "reports").rglob("research-report-*.json"))
            theses = list((root / "content_theses").rglob("content-thesis-card-*.json"))
            scripts = list((root / "script_drafts").rglob("script-draft-*.json"))
            self.assertTrue(reports and theses and scripts)

            # 10. a second session proves ungrounded fact-check quotes are
            # downgraded (never silently accepted as verified)
            view2 = flow.start_session("第二会话：夜间开放", [])
            sid2 = view2["session_id"]
            flow.add_source_url(sid2, "https://example.com/news/night-library")
            flow.add_source_text(
                sid2, "市财政局预算说明", SOURCE_B_TEXT,
                "https://example.gov.cn/budget/2027-culture",
            )
            flow.generate_research(sid2, "")
            provider_bad_fc = FakeWorkbenchLLM({})
            original_fc = provider_bad_fc.fact_check

            def bad_fc(report, sources):
                payload = original_fc(report, sources).data
                for check in payload["checks"]:
                    check["verification_notes"] = "原文载明「这段引文根本不在任何来源里出现过」。"
                return ProviderResult(
                    data=payload,
                    provenance=ProviderProvenance(search_calls=(), citations=()),
                )

            provider_bad_fc.fact_check = bad_fc
            bad_flow = self._flow(root, provider_bad_fc)
            bad_result = bad_flow.run_fact_check(sid2)
            self.assertGreater(bad_result["quote_downgraded_checks"], 0)


class AcquisitionFailureFlowTests(_UserSettingsIsolatedTestCase):
    """Round-2 Nexus regression: validly authorized download failures are
    durable unresolved references, not transient response-only errors."""

    def _configure(self, root: Path):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "chat",
            "chat_base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "api_key": "sk-test-key",
            "downloads_dir": str(root.resolve()),
        }))

    def _flow(self, root: Path):
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery_five,
            provider_factory=lambda settings: FakeWorkbenchLLM(settings),
            fetcher=_fake_fetcher,
        )

    def test_four_authorized_download_failures_remain_pending_and_retry_clears(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            bvids = [item["bvid"] for item in view["references"]]
            media = root / "reference-one.mp4"
            media.write_bytes(b"fixture-media")

            def acquire(reference, downloads_dir, authorization_text, **kwargs):
                if reference["bvid"] != bvids[0]:
                    raise acquisition.WorkbenchAcquisitionError(
                        "下载失败：模拟平台拒绝（不绕过平台限制）"
                    )
                record = _fake_acquirer(reference, downloads_dir, authorization_text)
                record["media_path"] = str(media)
                return record

            authorization = "我授权在本地研究使用这些参考视频。"
            with mock.patch.object(acquisition, "acquire_reference", acquire):
                result = flow.acquire_references(sid, bvids, authorization)
            self.assertEqual(sum(1 for item in result["results"] if item["ok"]), 1)
            self.assertEqual(sum(1 for item in result["results"] if not item["ok"]), 4)

            # The successful reference is treated as analyzed for this gate
            # regression; the four failures must still remain eligible/pending.
            flow.store.update(sid, lambda session: session["references"][bvids[0]].update({
                "status": "analyzed",
                "study_path": "",
            }))
            state = flow.view(sid)
            readiness = state["references_readiness"]
            self.assertEqual((readiness["analyzed"], readiness["eligible"]), (1, 5))
            self.assertEqual(readiness["failed"], 4)
            self.assertEqual(set(readiness["failed_bvids"]), set(bvids[1:]))
            self.assertEqual(set(readiness["pending_bvids"]), set(bvids[1:]))
            for bvid in bvids[1:]:
                persisted = flow.store.load(sid)["references"][bvid]
                self.assertEqual(persisted["status"], "failed")
                self.assertEqual(persisted["failure_stage"], "acquisition")
                self.assertIn("模拟平台拒绝", persisted["failure_reason"])
                self.assertEqual(persisted["authorization_text"], authorization)
                self.assertGreaterEqual(persisted["attempt_count"], 1)
                acquisition_record = json.loads(
                    (
                        flow.store.references_dir(sid) / bvid / "acquisition.json"
                    ).read_text(encoding="utf-8")
                )
                self.assertEqual(acquisition_record["status"], "failed")
                self.assertEqual(acquisition_record["failure_stage"], "acquisition")
                self.assertIn("模拟平台拒绝", acquisition_record["failure_reason"])
                visible = next(item for item in state["references"] if item["bvid"] == bvid)
                self.assertEqual(visible["study_status"], "failed")
                self.assertIn("模拟平台拒绝", visible["study_error"])

            flow.add_source_text(sid, "示例新闻社", SOURCE_A_TEXT, "https://example.com/news/night-library")
            flow.add_source_text(sid, "市财政局预算说明", SOURCE_B_TEXT, "https://example.gov.cn/budget/2027-culture")
            with self.assertRaises(WorkbenchFlowError) as blocked:
                flow.generate_research(sid, "")
            self.assertIn("1/5", str(blocked.exception))
            self.assertIn("失败", str(blocked.exception))

            partial = flow.generate_research(
                sid,
                "",
                allow_partial=True,
                partial_reason="四条参考下载失败，先基于已完成的一条继续研究",
            )
            self.assertTrue(partial["reference_comparison"]["partial"])
            stored = flow.store.load(sid)["research"]["reference_comparison"]
            self.assertEqual(set(stored["failed_bvids"]), set(bvids[1:]))
            self.assertIn("四条参考下载失败", stored["partial_reason"])

            # A later retry updates the same durable reference and removes the
            # current failure, so it is no longer an unresolved download.
            retry_bvid = bvids[1]

            def retry(reference, downloads_dir, authorization_text, **kwargs):
                if reference["bvid"] != retry_bvid:
                    raise acquisition.WorkbenchAcquisitionError("仍失败")
                record = _fake_acquirer(reference, downloads_dir, authorization_text)
                record["media_path"] = str(media)
                return record

            with mock.patch.object(acquisition, "acquire_reference", retry):
                flow.acquire_references(sid, [retry_bvid], authorization)
            retried = flow.store.load(sid)["references"][retry_bvid]
            self.assertEqual(retried["status"], "downloaded")
            self.assertNotIn("failure_reason", retried)

    def test_ui_shows_persisted_failure_reason_and_unresolved_count(self):
        html = (REPO / "src/deeptalk_studio/webui_static/index.html").read_text(encoding="utf-8")
        self.assertIn("study_error", html)
        self.assertIn("失败待重试", html)
        self.assertIn("readiness.failed", html)

    def test_failed_authorized_state_survives_new_flow_instance(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            bvid = view["references"][0]["bvid"]

            def deny(reference, downloads_dir, authorization_text, **kwargs):
                raise acquisition.WorkbenchAcquisitionError("下载失败：离线测试拒绝")

            with mock.patch.object(acquisition, "acquire_reference", deny):
                flow.acquire_references(sid, [bvid], "我授权在本地研究使用该参考视频。")
            restarted = self._flow(root)
            state = restarted.view(sid)
            self.assertEqual(state["references_readiness"]["eligible"], 1)
            self.assertEqual(state["references_readiness"]["failed"], 1)
            self.assertIn("离线测试拒绝", state["references"][0]["study_error"])


class ReferenceAnalysisStateTests(_UserSettingsIsolatedTestCase):
    def _configure(self, root):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "chat",
            "chat_base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "api_key": "sk-fixture",
            "downloads_dir": str(root),
        }))

    def test_llm_outage_is_unverified_then_reanalysis_reuses_transcript(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            view_counter = {"extract": 0, "whisper": 0}

            class FlakyProvider(FakeWorkbenchLLM):
                def __init__(self, settings):
                    super().__init__(settings)
                    self.summary_attempts = 0

                def summarize_reference(self, transcript_text, metrics, metadata):
                    self.summary_attempts += 1
                    if self.summary_attempts == 1:
                        raise WorkbenchLLMError("测试模型暂不可用", category="network")
                    return super().summarize_reference(transcript_text, metrics, metadata)

            provider = FlakyProvider({})
            flow = WorkbenchFlow(
                root,
                discovery_runner=lambda topic, urls: _fake_discovery(topic, urls, count=1),
                provider_factory=lambda settings: provider,
            )
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            bvid = view["references"][0]["bvid"]
            media = root / "reference.mp4"
            media.write_bytes(b"fixture-media")

            def acquire(reference, downloads_dir, authorization_text, **kwargs):
                record = _fake_acquirer(reference, downloads_dir, authorization_text)
                record["media_path"] = str(media)
                return record

            def audio_runner(command, **kwargs):
                view_counter["extract"] += 1
                Path(command[-1]).write_bytes(b"RIFF" + b"\x00" * 100)
                return _FakeCompleted(returncode=0)

            def whisper_runner(command, **kwargs):
                view_counter["whisper"] += 1
                base = Path(command[command.index("--output-file") + 1])
                base.with_suffix(".json").write_text(json.dumps({
                    "transcription": [
                        {"offset": 0, "duration": 4000, "text": "真实转写段落。"},
                    ],
                    "result": {"language": "zh"},
                }, ensure_ascii=False), encoding="utf-8")
                return _FakeCompleted(returncode=0)

            class Installation:
                runtime_path = "/usr/bin/true"
                model_path = "/models/large-v3.bin"
                dtw_preset = "none"
                model_name = "large-v3"
                runtime_version = "fixture"

            class Bootstrap:
                def ensure(self):
                    return Installation()

            flow.audio_runner = audio_runner
            flow.whisper_runner = whisper_runner
            flow.whisper_bootstrap = Bootstrap()
            with mock.patch.object(acquisition, "acquire_reference", acquire):
                flow.acquire_references(sid, [bvid], "我授权在本地研究使用该参考视频。")
                first = flow.analyze_reference(sid, bvid)
            self.assertEqual(first["study"]["analysis_status"], "unverified")
            state = flow.view(sid)
            self.assertEqual(state["references_readiness"]["analyzed"], 0)
            self.assertEqual(state["references"][0]["study_status"], "unverified")
            self.assertEqual(state["references"][0]["study"]["transcript_status"], "complete")
            self.assertEqual(state["references"][0]["study"]["transcript_provenance"]["model"], "large-v3")
            self.assertEqual(view_counter, {"extract": 1, "whisper": 1})

            second = flow.reanalyze_reference(sid, bvid)
            self.assertEqual(second["study"]["analysis_status"], "analyzed")
            self.assertEqual(flow.view(sid)["references_readiness"]["analyzed"], 1)
            self.assertEqual(view_counter, {"extract": 1, "whisper": 1})

    def test_ui_exposes_unverified_retry_and_transcript_segments(self):
        html = (REPO / "src/deeptalk_studio/webui_static/index.html").read_text(encoding="utf-8")
        self.assertIn("unverified", html)
        self.assertIn("重新分析", html)
        self.assertIn("segments", html)


class ThesisPromptTests(_UserSettingsIsolatedTestCase):
    """Real prompt builders must work end to end (fakes bypass them, so a
    broken import or rendering would otherwise only surface at runtime)."""

    def test_build_thesis_writer_prompt_renders_comparison(self):
        from deeptalk_studio.workbench.prompts import (
            serialize_reference_insights,
        )
        from deeptalk_studio.thesis_prompt import build_thesis_writer_prompt

        study = {
            "bvid": "BV1x",
            "title": "测试参考视频",
            "view_count": 1000,
            "duration_seconds": 120,
            "cps": 5.0,
            "question_count": 2,
            "narrative_summary": "以问题开场，先事实后分析。",
            "creator_viewpoint": "先摆事实再鲜明评判的评论视角。",
            "hook_style": "直接提问式钩子",
            "pacing": "中速",
            "struct_patterns": ["问题—事实—评价"],
            "takeaways": ["开场给全信息量"],
        }
        report = {"claims": [], "limitations": [], "open_questions": []}
        prompt = build_thesis_writer_prompt(report, serialize_reference_insights([study]))
        self.assertIn("参考视频叙事与观点对比", prompt)
        self.assertIn("可归因观点：先摆事实再鲜明评判的评论视角。", prompt)
        self.assertIn("差异化定位", prompt)

    def test_build_research_prompt_renders_comparison(self):
        from deeptalk_studio.workbench.prompts import (
            build_workbench_research_user_prompt,
            serialize_reference_insights,
        )

        study = {
            "bvid": "BV1x",
            "title": "测试参考视频",
            "view_count": 1000,
            "duration_seconds": 120,
            "narrative_summary": "以问题开场，先事实后分析。",
            "creator_viewpoint": "批评立场，聚焦后续处理。",
            "hook_style": "直接提问式钩子",
            "struct_patterns": ["问题—事实—评价"],
        }
        prompt = build_workbench_research_user_prompt(
            "主题", "问题？", [], serialize_reference_insights([study])
        )
        self.assertIn("参考视频叙事与观点对比", prompt)
        self.assertIn("批评立场，聚焦后续处理。", prompt)
        self.assertIn("绝不作为事实来源", prompt)


class NetFetchTests(_UserSettingsIsolatedTestCase):
    """Issue #23 B2: user-supplied source URLs may only reach public
    HTTP(S) destinations (no loopback/private/link-local SSRF, no rebinding
    window, no proxy bypass, no non-http redirect targets)."""

    def test_rejects_non_http_schemes(self):
        from deeptalk_studio.workbench import netfetch

        for url in ("ftp://example.com/x", "file:///etc/passwd", "gopher://example.com"):
            result = netfetch.fetch_public_source(url)
            self.assertFalse(result["ok"], url)
            self.assertIn("拒绝", result["error"])

    def test_rejects_private_ip_literals_without_any_socket(self):
        from deeptalk_studio.workbench import netfetch

        for url in (
            "http://127.0.0.1/x",
            "http://127.0.0.1:8931/v1/models",
            "http://10.0.0.5/x",
            "http://192.168.1.1/",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/",
            "http://[fe80::1]/",
            "http://0.0.0.0/",
            "http://224.0.0.1/",
            "http://192.0.2.10/doc",           # TEST-NET-1 (documentation)
            "http://100.64.0.1/cgnat",         # shared address space
        ):
            result = netfetch.fetch_public_source(url)
            self.assertFalse(result["ok"], url)
            self.assertIn("公网", result["error"], url)

    def test_rejects_hostnames_resolving_to_private_space(self):
        import socket

        from deeptalk_studio.workbench import netfetch

        def to_loopback(host, port, *args):
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", port))]

        def mixed(host, port, *args):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port)),
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.1.2.3", port)),
            ]

        def no_answer(host, port, *args):
            return []

        def dns_error(host, port, *args):
            raise socket.gaierror("rebinding uncertainty")

        expectations = {
            "loopback": ("公网",),
            "mixed_private": ("公网",),
            "no_answer": ("未解析出任何公网地址",),
            "dns_error": ("无法解析", "不确定性即失败"),
        }
        for name, resolver in (
            ("loopback", to_loopback),
            ("mixed_private", mixed),
            ("no_answer", no_answer),
            ("dns_error", dns_error),
        ):
            result = netfetch.fetch_public_source("http://source.example/x", resolver=resolver)
            self.assertFalse(result["ok"], name)
            for fragment in expectations[name]:
                self.assertIn(fragment, result["error"], name)

    def test_public_resolution_is_pinned_and_dials_only_validated_ips_offline(self):
        import socket

        from deeptalk_studio.workbench import netfetch

        class OfflineSocket:
            attempts = []

            def __init__(self, *args):
                self.closed = False

            def settimeout(self, _timeout):
                return None

            def setsockopt(self, *_args):
                return None

            def bind(self, _source_address):
                return None

            def connect(self, sockaddr):
                self.attempts.append(sockaddr)
                raise OSError("offline socket fixture")

            def close(self):
                self.closed = True

        # A public answer passes validation; the fake dial then fails fast.
        # Any *second* resolver answer that flips private never reaches the
        # socket because the connection is pinned to the first validated list.
        calls = []

        def rebind_after_first(host, port, *args):
            calls.append(host)
            if len(calls) == 1:
                return [
                    (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
                ]
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", port))]

        connection = netfetch._PinnedHTTPConnection("rebind.example", 80, timeout=0.2)
        connection.resolver = rebind_after_first
        with mock.patch.object(netfetch.socket, "socket", OfflineSocket):
            with self.assertRaises(netfetch.WorkbenchSourceFetchError) as ctx:
                connection.connect()
        # 证词：连接只拨向第一个（也是唯一的）已验证公网地址，从未重解析。
        self.assertEqual(len(calls), 1)
        self.assertEqual(OfflineSocket.attempts, [("93.184.216.34", 80)])
        self.assertIn("无法连接任何已验证的公网地址", str(ctx.exception))

    def test_redirect_to_loopback_or_private_is_rejected_offline(self):
        """Every HTTP(S) redirect target is resolved before any socket dial."""
        from email.message import Message
        import socket

        from deeptalk_studio.workbench import netfetch

        class OfflineSocket:
            attempts = []

            def __init__(self, *args):
                self.closed = False

            def settimeout(self, _timeout):
                return None

            def setsockopt(self, *_args):
                return None

            def bind(self, _source_address):
                return None

            def connect(self, sockaddr):
                self.attempts.append(sockaddr)

            def close(self):
                self.closed = True

        class FakeResponse:
            def __init__(self, status, url, headers=None, body=b"fixture"):
                self.status = status
                self.code = status
                self.reason = "Found" if status in (301, 302, 303, 307, 308) else "OK"
                self.msg = self.reason
                self.headers = Message()
                for key, value in (headers or {}).items():
                    self.headers[key] = value
                self._url = url
                self._body = body

            def read(self, amount=-1):
                return self._body if amount < 0 else self._body[:amount]

            def geturl(self):
                return self._url

            def info(self):
                return self.headers

            def getcode(self):
                return self.code

            def close(self):
                return None

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        addresses = {
            "public.example": "93.184.216.34",
            "public-redirect.example": "93.184.216.35",
            "loopback.example": "127.0.0.1",
            "private.example": "10.1.2.3",
        }

        for target_url, target_host, rejected_ip in (
            ("https://public-redirect.example/final", "public-redirect.example", ""),
            ("http://loopback.example/private", "loopback.example", "127.0.0.1"),
            ("https://private.example/internal", "private.example", "10.1.2.3"),
        ):
            with self.subTest(target_url=target_url):
                resolver_calls = []
                OfflineSocket.attempts = []

                def resolver(host, port, *args):
                    resolver_calls.append(host)
                    return [(
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        socket.IPPROTO_TCP,
                        "",
                        (addresses[host], port),
                    )]

                def fake_request(
                    connection,
                    method,
                    selector,
                    body=None,
                    headers=None,
                    *,
                    encode_chunked=False,
                ):
                    connection.sock = connection._pinned_create_connection(
                        (connection.host, connection.port),
                        connection.timeout,
                        connection.source_address,
                    )
                    if connection.host == "public.example":
                        connection._fixture_response = FakeResponse(
                            302,
                            "http://public.example/start",
                            {"Location": target_url},
                        )
                    else:
                        connection._fixture_response = FakeResponse(
                            200,
                            target_url,
                            {"Content-Type": "text/plain"},
                            b"public redirect fixture body " * 3,
                        )

                def fake_getresponse(connection):
                    return connection._fixture_response

                with (
                    mock.patch.object(netfetch._PinnedHTTPConnection, "request", fake_request),
                    mock.patch.object(netfetch._PinnedHTTPConnection, "getresponse", fake_getresponse),
                    mock.patch.object(netfetch.socket, "socket", OfflineSocket),
                ):
                    result = netfetch.fetch_public_source(
                        "http://public.example/start", resolver=resolver
                    )

                if rejected_ip:
                    self.assertFalse(result["ok"])
                    self.assertIn(rejected_ip, result["error"])
                else:
                    self.assertTrue(result["ok"], result)
                    self.assertEqual(result["final_url"], target_url)
                self.assertEqual(resolver_calls, ["public.example", target_host])
                expected_attempts = [("93.184.216.34", 80)]
                if not rejected_ip:
                    expected_attempts.append(("93.184.216.35", 443))
                self.assertEqual(OfflineSocket.attempts, expected_attempts)

    def test_redirect_guard_rejects_non_http_targets(self):
        import urllib.request

        from deeptalk_studio.workbench import netfetch

        handler = netfetch._StrictRedirectHandler()
        request = urllib.request.Request("http://public.example/a")
        for bad_target in ("ftp://example.com/x", "file:///etc/passwd"):
            with self.assertRaises(netfetch.WorkbenchSourceFetchError):
                handler.redirect_request(request, None, 302, "Found", None, bad_target)
        allowed = handler.redirect_request(request, None, 302, "Found", None, "http://other.example/b")
        self.assertIsInstance(allowed, urllib.request.Request)
        self.assertEqual(handler.max_redirections, netfetch.MAX_REDIRECTS)

    def test_fetch_public_source_ignores_environment_proxies(self):
        # Even with proxy env vars set, the fetcher must dial directly
        # (a proxy would bypass the public-IP validation).
        import os
        import socket

        from deeptalk_studio.workbench import netfetch

        old = {key: os.environ.get(key) for key in ("http_proxy", "HTTP_PROXY")}
        try:
            os.environ["http_proxy"] = "http://127.0.0.1:7897"
            os.environ["HTTP_PROXY"] = "http://127.0.0.1:7897"

            def resolver_local(host, port, *args):
                return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("192.168.0.10", port))]

            result = netfetch.fetch_public_source(
                "http://internal.example/x", resolver=resolver_local, timeout=0.2
            )
            self.assertFalse(result["ok"])
            # 192.168.0.10 (private) rejected — NOT the loopback proxy address,
            # proving the connection did not go via the configured proxy.
            self.assertIn("192.168.0.10", result["error"])
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class TopicConsistencyTests(_UserSettingsIsolatedTestCase):
    """Issue #23 B1: off-topic research/thesis/script must fail closed at
    generation AND approval/delivery boundaries — the exact observed E2E
    mismatch was a Moscow University topic with a library-themed payload."""

    def _flow(self, root: Path, provider=None):
        provider = provider or FakeWorkbenchLLM
        return WorkbenchFlow(
            root,
            discovery_runner=_fake_discovery,
            provider_factory=lambda settings: provider(settings)
            if isinstance(provider, type)
            else provider,
            fetcher=_fake_fetcher,
            acquire_runner=None,
            audio_runner=None,
            whisper_runner=None,
        )

    def _configure(self, root: Path):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "chat",
            "chat_base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "api_key": "sk-test-key",
            "downloads_dir": str(root.resolve()),
        }))

    def test_off_topic_research_is_rejected_not_relabelled(self):
        """The observed mismatch: Moscow session topic + library payload
        (fixtures) — research must not even be saved, let alone approved."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("莫斯科大学留学生旭日旗事件", [])
            sid = view["session_id"]
            flow.add_source_text(
                sid, "示例新闻社：图书馆夜间开放", SOURCE_A_TEXT,
                "https://example.com/news/night-library",
            )
            flow.add_source_text(
                sid, "市财政局预算说明", SOURCE_B_TEXT,
                "https://example.gov.cn/budget/2027-culture",
            )
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.generate_research(sid, "")
            self.assertIn("选题主题明显不符", str(ctx.exception))
            # nothing was written: no draft, no approval possible
            session = flow.store.load(sid)
            self.assertEqual(session["research"]["status"], "not_started")
            self.assertFalse(session["research"]["draft_path"])
            state = flow.view(sid)
            self.assertEqual(state["references_readiness"]["analyzed"], 0)
            self.assertEqual(state["references_readiness"]["eligible"], 0)

    def test_off_topic_report_cannot_be_approved_and_cannot_drive_script(self):
        """A topical session produces a reviewed report; if the session topic
        then diverges from the saved report (tampering/off-topic boundaries),
        approval and script generation must both fail closed."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            flow.add_source_text(
                sid, "示例新闻社", SOURCE_A_TEXT, "https://example.com/news/night-library"
            )
            flow.add_source_text(
                sid, "市财政局预算说明", SOURCE_B_TEXT,
                "https://example.gov.cn/budget/2027-culture",
            )
            flow.generate_research(sid, "")
            flow.run_fact_check(sid)
            # flip the session topic: the saved review is now off-topic
            flow.store.update(sid, lambda s: s.update({"topic": "莫斯科大学留学生旭日旗事件"}))
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.approve_research(sid, "我确认研究结论，批准进入写稿。")
            self.assertIn("选题主题明显不符", str(ctx.exception))
            self.assertIn("待批准的研究报告", str(ctx.exception))

    def test_off_topic_thesis_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            # library topic + Moscow-themed thesis payload → reject
            class ForeignThesisProvider(FakeWorkbenchLLM):
                def write_thesis(self, report, narrative_insights=None):
                    from deeptalk_studio.schema import (
                        THESIS_CONTENT_JSON_SCHEMA,
                    )

                    data = {
                        "core_question": "莫斯科大学旭日旗事件该怎么看？",
                        "one_sentence_answer": "先分清证据层级。",
                        "core_thesis": "莫斯科大学事件的定性要等校方程序。",
                        "counterintuitive_point": "最响亮的说法不等于最重的证据。",
                        "target_emotion": "清醒克制",
                        "resonance": "反感被带节奏",
                        "approval_point": "肯定群体立场正当",
                        "comment_tension": "严惩与程序",
                        "spokesperson_value": "替观众排队信息",
                        "value_identity": "讲证据层级",
                        "strongest_evidence_claim_ids": ["C2"],
                        "counter_evidence_claim_ids": ["C1"],
                        "uncertainty_limits": list(report["limitations"]),
                        "crowded_angles": ["不做情绪宣泄"],
                        "differentiated_angle": "按证据层级讲莫斯科大学事件。",
                        "hook_promise": "三个问题开场。",
                        "ending_question_or_judgment": "等权威披露再判断。",
                        "competitive_insight_notes": ["参考观点仅作对比。"],
                    }
                    validate_json_schema(data, THESIS_CONTENT_JSON_SCHEMA, "deep_talk_thesis_content")
                    return ProviderResult(
                        data=data,
                        provenance=ProviderProvenance(search_calls=(), citations=()),
                    )

            flow = self._flow(root, ForeignThesisProvider)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            flow.add_source_text(
                sid, "示例新闻社", SOURCE_A_TEXT, "https://example.com/news/night-library"
            )
            flow.add_source_text(
                sid, "市财政局预算说明", SOURCE_B_TEXT,
                "https://example.gov.cn/budget/2027-culture",
            )
            flow.generate_research(sid, "")
            flow.run_fact_check(sid)
            flow.approve_research(sid, "我确认研究结论，批准进入写稿。")
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.generate_thesis(sid)
            self.assertIn("选题主题明显不符", str(ctx.exception))
            session = flow.store.load(sid)
            self.assertEqual(session["thesis"]["status"], "not_started")

    def test_topical_paraphrase_still_passes(self):
        """Semantic paraphrase must NOT be rejected: a report that omits the
        literal topic string but keeps the key entities still passes."""
        from deeptalk_studio.workbench.flow import (
            MIN_TOPIC_COVERAGE,
            ensure_topic_consistency,
        )

        coverage = ensure_topic_consistency(
            "莫斯科大学留学生旭日旗事件",
            [
                "一名在莫斯科国立大学就读的中国留学生身披旭日旗后公开道歉，"
                "留学生群体递交联名信，校方通报开除学籍并办理遣返。"
            ],
            what="测试",
        )
        self.assertGreaterEqual(coverage, MIN_TOPIC_COVERAGE)

    def test_adjacent_keyword_topic_is_rejected(self):
        """Shared generic bigrams must not make a neighboring topic pass."""
        from deeptalk_studio.workbench.flow import ensure_topic_consistency

        with self.assertRaises(WorkbenchFlowError):
            ensure_topic_consistency(
                "莫斯科大学留学生旭日旗事件",
                ["大学留学生考试事件：校方公布考场纪律与成绩复核安排。"],
                what="测试",
            )

    def test_report_topic_metadata_cannot_mask_off_topic_body(self):
        """A model-controlled ``topic`` field is not evidence of alignment."""
        from deeptalk_studio.workbench.flow import (
            _report_topic_texts,
            ensure_topic_consistency,
        )

        report = {
            "topic": "莫斯科大学留学生旭日旗事件",
            "research_question": "大学留学生考试事件该如何处理？",
            "scope_summary": "讨论考试纪律、成绩复核与校方程序。",
            "executive_summary": "校方公布考试安排并接受复核申请。",
            "claims": [{"claim": "考试违规由学校依规处理。"}],
            "sources": [{"title": "大学考试通知", "stance_summary": "说明考试流程。"}],
        }
        with self.assertRaises(WorkbenchFlowError):
            ensure_topic_consistency(
                "莫斯科大学留学生旭日旗事件",
                _report_topic_texts(report),
                what="测试报告",
            )


class ReferenceSynthesisTests(_UserSettingsIsolatedTestCase):
    """Issue #23 B3: analyzed-N/eligible-M readiness, explicit
    partial-analysis override, and the deterministic five-way viewpoint
    comparison injected into research + thesis."""

    def _flow(self, root: Path, provider=None, discovery=_fake_discovery):
        provider = provider or FakeWorkbenchLLM
        return WorkbenchFlow(
            root,
            discovery_runner=discovery,
            provider_factory=lambda settings: provider(settings)
            if isinstance(provider, type)
            else provider,
            fetcher=_fake_fetcher,
            acquire_runner=None,
            audio_runner=None,
            whisper_runner=None,
        )

    def _configure(self, root: Path):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "chat",
            "chat_base_url": "https://llm.example.com/v1",
            "model": "test-model",
            "api_key": "sk-test-key",
            "downloads_dir": str(root.resolve()),
        }))

    def _mark_downloaded(self, flow, sid, bvids):
        def mutate(session):
            for bvid in bvids:
                session["references"].setdefault(bvid, {})
                session["references"][bvid]["status"] = "downloaded"
                session["references"][bvid]["media_path"] = str(Path("/tmp/fake-%s.mp4" % bvid))
                session["references"][bvid]["title"] = "测试参考 %s" % bvid
                session["references"][bvid]["url"] = "https://www.bilibili.com/video/%s" % bvid

        flow.store.update(sid, mutate)

    def _mark_analyzed(self, flow, sid, bvid, viewpoint="测试观点：先事实后评判。"):
        ref_dir = flow.store.references_dir(sid) / bvid
        ref_dir.mkdir(parents=True, exist_ok=True)
        study = {
            "bvid": bvid,
            "title": "测试参考 %s" % bvid,
            "view_count": 1234,
            "duration_seconds": 100.0,
            "cps": 5.2,
            "question_count": 3,
            "narrative_summary": "以问题开场，先事实后分析，结尾回扣。",
            "creator_viewpoint": viewpoint,
            "hook_style": "直接提问式钩子",
            "pacing": "中速",
            "struct_patterns": ["问题—事实—评价", "结尾回扣"],
            "takeaways": ["开场给全信息量"],
        }
        path = ref_dir / "study.json"
        path.write_text(json.dumps(study, ensure_ascii=False), encoding="utf-8")

        def mutate(session):
            session["references"].setdefault(bvid, {})
            session["references"][bvid]["status"] = "analyzed"
            session["references"][bvid]["study_path"] = str(path)
            session["references"][bvid]["media_path"] = str(Path("/tmp/fake-%s.mp4" % bvid))
            session["references"][bvid]["title"] = "测试参考 %s" % bvid
            session["references"][bvid]["url"] = "https://www.bilibili.com/video/%s" % bvid

        flow.store.update(sid, mutate)

    def test_research_blocked_until_analysis_complete_or_explicit_override(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            flow = self._flow(root)
            view = flow.start_session("本市图书馆夜间开放试点", [], )
            sid = view["session_id"]
            self._mark_downloaded(flow, sid, ["BV1test1", "BV1test2"])
            self._mark_analyzed(flow, sid, "BV1test1")
            flow.add_source_text(
                sid, "示例新闻社", SOURCE_A_TEXT, "https://example.com/news/night-library"
            )
            flow.add_source_text(
                sid, "市财政局预算说明", SOURCE_B_TEXT,
                "https://example.gov.cn/budget/2027-culture",
            )
            # 1/2 analyzed → blocked without override
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.generate_research(sid, "")
            self.assertIn("参考分析尚未完成", str(ctx.exception))
            self.assertIn("1/2", str(ctx.exception))
            # override requires a real reason
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.generate_research(sid, "", allow_partial=True, partial_reason="短")
            self.assertIn("理由", str(ctx.exception))
            # explicit override proceeds and records the honest partial state
            result = flow.generate_research(
                sid, "",
                allow_partial=True,
                partial_reason="本地转写中断，先基于已完成的 1 条参考继续研究",
            )
            self.assertEqual(result["reference_comparison"]["analyzed"], 1)
            self.assertEqual(result["reference_comparison"]["eligible"], 2)
            self.assertTrue(result["reference_comparison"]["partial"])
            stored = flow.store.load(sid)["research"]["reference_comparison"]
            self.assertTrue(stored["partial"])
            self.assertIn("1 条参考", stored["partial_reason"])
            self.assertEqual(stored["bvids"], ["BV1test1"])

    def test_full_five_analysis_injects_comparison_and_chains_to_script(self):
        """Deterministic full-five regression: all five authorized references
        analyzed → no override needed → research and thesis prompts carry the
        five-way comparison → chain completes to a reviewed, topical script
        whose delivery view reports the honest 5/5 synthesis."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._configure(root)
            provider = FakeWorkbenchLLM({})
            flow = self._flow(root, provider=provider, discovery=_fake_discovery_five)
            view = flow.start_session("本市图书馆夜间开放试点", [])
            sid = view["session_id"]
            bvids = ["BV1test%d" % index for index in range(1, 6)]
            self._mark_downloaded(flow, sid, bvids)
            viewpoints = [
                "观点一：聚焦预算金额与性价比。",
                "观点二：关注服务人群定位。",
                "观点三：强调评估机制缺位。",
                "观点四：反对仓促续期或取消。",
                "观点五：支持试行但要求公开数据。",
            ]
            for bvid, viewpoint in zip(bvids, viewpoints):
                self._mark_analyzed(flow, sid, bvid, viewpoint=viewpoint)
            flow.add_source_text(
                sid, "示例新闻社", SOURCE_A_TEXT, "https://example.com/news/night-library"
            )
            flow.add_source_text(
                sid, "市财政局预算说明", SOURCE_B_TEXT,
                "https://example.gov.cn/budget/2027-culture",
            )
            # readiness 5/5 → no override allowed/needed; research proceeds
            readiness = flow.view(sid)["references_readiness"]
            self.assertEqual((readiness["analyzed"], readiness["eligible"]), (5, 5))
            result = flow.generate_research(sid, "钱怎么花，谁来评？")
            cmp = result["reference_comparison"]
            self.assertEqual((cmp["analyzed"], cmp["eligible"]), (5, 5))
            self.assertEqual(cmp["viewpoint_count"], 5)
            self.assertFalse(cmp["partial"])

            # the provider received the enriched five-way comparison
            insights = provider.received_reference_insights
            provider_insights = [insight for call in insights for insight in call]
            self.assertGreaterEqual(len(provider_insights), 5)
            for viewpoint in viewpoints:
                self.assertTrue(
                    any(viewpoint in str(i.get("creator_viewpoint", "")) for i in provider_insights),
                    viewpoint,
                )
            from deeptalk_studio.workbench.prompts import (
                build_workbench_research_user_prompt,
                render_reference_comparison,
            )

            block = render_reference_comparison(provider_insights[:5])
            self.assertIn("可归因观点", block)
            self.assertIn("N 方对比小结", block)
            self.assertIn("问题—事实—评价（5/5 条）", block)
            prompt = build_workbench_research_user_prompt(
                "本市图书馆夜间开放试点", "钱怎么花？", [], provider_insights[:5]
            )
            self.assertIn("参考视频叙事与观点对比", prompt)
            self.assertIn("禁止拼凑或复述", prompt)

            # full chain to a reviewed script with honest synthesis metadata
            flow.run_fact_check(sid)
            flow.approve_research(sid, "我确认研究结论，批准进入写稿。")
            thesis = flow.generate_thesis(sid)
            self.assertEqual(thesis["status"], "draft")
            # thesis call also received the comparison
            self.assertTrue(
                any(
                    "观点" in str(i.get("creator_viewpoint", ""))
                    for call in insights
                    for i in call
                )
            )
            review = flow.review_thesis(sid)
            self.assertEqual(review["gate_decision"], "pass", review)
            confirmed = flow.approve_thesis(
                sid, "我确认本期内容方向与选题卡一致，确认进入写稿。"
            )
            self.assertEqual(confirmed["status"], "approved_for_script")
            script = flow.generate_script(sid)
            self.assertEqual(script["status"], "reviewed", script)
            self.assertEqual(script["gate_status"], "pass")
            synthesis = script["reference_synthesis"]
            self.assertEqual((synthesis["analyzed"], synthesis["eligible"]), (5, 5))
            self.assertEqual(synthesis["viewpoint_count"], 5)
            self.assertFalse(synthesis["partial"])
            final = flow.final_script(sid)
            self.assertIn("夜间图书馆", final["teleprompter_text"])
            self.assertEqual(final["reference_synthesis"]["eligible"], 5)
            stored = flow.store.load(sid)["research"]["reference_comparison"]
            self.assertEqual(len(stored["bvids"]), 5)
            self.assertFalse(stored["partial"])


class StreamChatLLM:
    """离线流式夹具：记录调用并逐段产出剧本化增量（无任何网络请求）。"""

    def __init__(self, chunks, calls, *, fail_on=None):
        self.chunks = list(chunks)
        self.calls = calls
        self.fail_on = fail_on

    def chat_stream(self, messages):
        self.calls.append(("chat_stream", [m.get("role") for m in messages]))
        if self.fail_on:
            raise WorkbenchLLMError(self.fail_on, category="http_error", http_status=401)
        for chunk in self.chunks:
            yield chunk


class CreativeChatTests(_UserSettingsIsolatedTestCase):
    """Issue #44 chat-first MVP：真实流式协议（注入离线 transport）、
    多轮恢复、Creative Draft 修订与 canonical 门禁隔离。"""

    def _flow(self, root, llm):
        calls = []
        llm.calls = calls
        return WorkbenchFlow(root, provider_factory=lambda settings: llm), calls

    def _configure(self, root):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "deepseek",
            "api_key": "sk-chat-fixture",
        }))

    def test_chat_stream_persists_turns_and_recovers_after_reload(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, calls = self._flow(root, StreamChatLLM(["晚上", "好，", "聊聊选题。"], []))
            self._configure(root)
            context = flow.chat_send_start("你好，想聊聊夜间城市选题", [{"url": "https://example.com/a"}])
            self.assertEqual(context["user_turn"]["role"], "user")
            self.assertEqual(context["user_turn"]["links"][0]["status"], "unknown")
            events = list(flow.chat_stream_reply(context))
            deltas = [e["text"] for e in events if e["type"] == "delta"]
            done = [e for e in events if e["type"] == "done"]
            self.assertEqual(deltas, ["晚上", "好，", "聊聊选题。"])
            self.assertEqual(len(done), 1)
            assistant = done[0]["turn"]
            self.assertEqual(assistant["role"], "assistant")
            self.assertEqual(assistant["content"], "晚上好，聊聊选题。")
            self.assertEqual(assistant["model"], "deepseek-flash")
            self.assertEqual(assistant["provider_kind"], "fixture")
            # 重载后精确恢复（新 flow 实例读同一存储）
            reloaded = WorkbenchFlow(root, provider_factory=lambda s: None).chat_state()["chat"]
            self.assertEqual([t["role"] for t in reloaded["turns"]], ["user", "assistant"])
            self.assertEqual(reloaded["turns"][0]["links"][0]["url"], "https://example.com/a")
            # 只有一次模型调用（无隐藏重复计费）
            self.assertEqual([c[0] for c in calls], ["chat_stream"])
            # 多轮上下文：第二条消息带上完整历史
            context2 = flow.chat_send_start("第二轮追问")
            list(flow.chat_stream_reply(context2))
            roles = calls[-1][1]
            self.assertEqual(roles[:3], ["system", "user", "assistant"])
            self.assertEqual(roles[-1], "user")

    def test_chat_stream_stop_writes_no_assistant_turn_and_never_auto_retries(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, calls = self._flow(root, StreamChatLLM(["第一段", "第二段", "第三段"], []))
            self._configure(root)
            context = flow.chat_send_start("聊一半就停")
            events = flow.chat_stream_reply(context)
            first = next(events)
            self.assertEqual(first["type"], "delta")
            events.close()  # 用户停止/浏览器断开
            chat = flow.chat_state()["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user"])
            # 没有自动重试：模型只被调用一次（停止后）
            self.assertEqual(len(calls), 1)

    def test_chat_requires_configured_model_before_any_model_call(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, calls = self._flow(root, StreamChatLLM(["x"], []))
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.chat_send_start("没有 Key 的消息")
            message = str(ctx.exception)
            self.assertIn("API Key", message)
            self.assertNotIn("WAITING_FOR_OWNER_API_KEY", message)
            self.assertEqual(calls, [])  # 未配置时绝不发起模型调用

    def test_chat_empty_message_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["x"], []))
            self._configure(root)
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.chat_send_start("   ")
            self.assertIn("不能为空", str(ctx.exception))

    def test_draft_generate_edit_and_immutable_revisions(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["草稿正文第一版"], []))
            self._configure(root)
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.chat_draft_generate()
            self.assertIn("还没有可整理的对话", str(ctx.exception))
            context = flow.chat_send_start("请帮我整理个草稿")
            list(flow.chat_stream_reply(context))
            result = flow.chat_draft_generate()
            draft1 = result["draft"]
            self.assertEqual(draft1["schema"], "creative-draft/1")
            self.assertEqual(draft1["status"], "unreviewed")
            self.assertEqual(draft1["revision"], 1)
            self.assertEqual(draft1["origin"], "model")
            self.assertEqual(draft1["origin_turn_id"], "t2")
            # 用户自由编辑 → 追加新 revision，旧 revision 不可变
            result2 = flow.chat_draft_save("我在草稿上自由修改过的第二版")
            draft2 = result2["draft"]
            self.assertEqual(draft2["revision"], 2)
            self.assertEqual(draft2["origin"], "user_edit")
            drafts = flow.chat_state()["chat"]["drafts"]
            self.assertEqual([d["revision"] for d in drafts], [1, 2])
            self.assertEqual(drafts[0]["content"], "草稿正文第一版")
            # 没有草稿内容为空
            with self.assertRaises(WorkbenchFlowError):
                flow.chat_draft_save("  ")

    def test_draft_is_isolated_from_canonical_gates_and_cannot_masquerade(self):
        """Nexus 第 4 点：草稿绝不写 canonical approved/reviewed 路径，
        不解锁正式生产；canonical 门禁保持 fail-closed。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["草稿内容"], []))
            self._configure(root)
            context = flow.chat_send_start("选题讨论")
            list(flow.chat_stream_reply(context))
            flow.chat_draft_generate()
            flow.chat_draft_save("人工编辑版")
            # 聊天/草稿不会创建 canonical workbench 会话
            self.assertIsNone(flow.store.load_latest())
            # 草稿存储中不存在任何 canonical 门禁字段
            chat_file = json.dumps(flow.chat_state()["chat"], ensure_ascii=False)
            for forbidden in (
                "reviewed_path",
                "approved_path",
                "gate_status",
                "quality",
            ):
                self.assertNotIn(forbidden, chat_file)
            # canonical 定稿在没有正式会话时依旧 fail-closed
            with self.assertRaises(Exception) as ctx:
                flow.final_script("no-such-session")
            self.assertIn("会话", str(ctx.exception))

    def test_chat_storage_permissions_are_restricted_and_secret_free(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["内容"], []))
            self._configure(root)
            context = flow.chat_send_start("包含秘密吗")
            list(flow.chat_stream_reply(context))
            # 聊天历史存用户级稳定目录（issuecomment-6366157284，本测试类
            # 已注入隔离目录）；0600 权限与「无 Key 落盘」不变。
            chat_dir = flow.creative.directory
            files = list(chat_dir.glob("*.json"))
            self.assertEqual(len(files), 1)
            mode = files[0].stat().st_mode & 0o777
            self.assertEqual(mode, 0o600)
            self.assertNotIn("sk-chat-fixture", files[0].read_text(encoding="utf-8"))

    def test_multiple_sessions_are_fully_isolated(self):
        """多会话（issuecomment-6366157284）：新建会话零污染、选中会话的
        turns/草稿完全独立、操作绝不静默回落 latest、列表元数据正确、
        会话间互不覆盖。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            class SequencedChatLLM:
                def __init__(self, replies):
                    self.replies = [list(r) for r in replies]
                    self.calls = []

                def chat_stream(self, messages):
                    self.calls.append([dict(m) for m in messages])
                    idx = min(len(self.calls) - 1, len(self.replies) - 1)
                    for piece in self.replies[idx]:
                        yield piece

            llm = SequencedChatLLM([
                ["A 的回复"], ["甲草稿正文"], ["B 的回复"], ["B 的追问回复"],
            ])
            flow, _ = self._flow(root, llm)
            self._configure(root)
            # 会话 A：发送 + 回复 + 草稿 + 二次编辑
            ctx_a = flow.chat_send_start("话题甲：城市夜间自习空间")
            session_a = str(ctx_a["session"]["session_id"])
            list(flow.chat_stream_reply(ctx_a))
            flow.chat_draft_generate(session_a)
            flow.chat_draft_save("甲草稿的第二次修改", session_a)
            # 「新建对话」首发送才创建新会话（点击新建零服务端调用）
            ctx_b = flow.chat_send_start("话题乙：通勤路上的观察", new_session=True)
            session_b = str(ctx_b["session"]["session_id"])
            self.assertNotEqual(session_a, session_b)
            list(flow.chat_stream_reply(ctx_b))
            # B 与 A 完全隔离：B 无 A 的任何内容/草稿
            chat_b = flow.chat_state(session_b)["chat"]
            self.assertEqual([t["content"] for t in chat_b["turns"]],
                             ["话题乙：通勤路上的观察", "B 的回复"])
            self.assertEqual(chat_b["drafts"], [])
            chat_a = flow.chat_state(session_a)["chat"]
            self.assertEqual([t["content"] for t in chat_a["turns"]][0], "话题甲：城市夜间自习空间")
            self.assertEqual(len(chat_a["drafts"]), 2)
            # 回退 latest 兼容路径仍指向最近更新的会话 B
            self.assertEqual(flow.chat_state()["chat"]["session_id"], session_b)
            # 在 B 继续回复不影响 A
            ctx_b2 = flow.chat_send_start("继续乙话题", session_id=session_b)
            list(flow.chat_stream_reply(ctx_b2))
            self.assertEqual(len(flow.chat_state(session_a)["chat"]["turns"]), 2)
            self.assertEqual(len(flow.chat_state(session_b)["chat"]["turns"]), 4)
            # 列表：按最近更新倒序，标题取首条用户消息，计数正确
            sessions = flow.chat_sessions()["sessions"]
            self.assertEqual(sessions[0]["session_id"], session_b)
            self.assertEqual(sessions[0]["title"], "话题乙：通勤路上的观察")
            self.assertEqual(sessions[0]["turns"], 4)
            self.assertEqual(sessions[1]["session_id"], session_a)
            self.assertEqual(sessions[1]["drafts"], 2)
            # 重载后（新 flow 实例）两会话仍精确恢复
            fresh = WorkbenchFlow(root, provider_factory=lambda s: None)
            self.assertEqual(len(fresh.chat_state(session_a)["chat"]["drafts"]), 2)
            self.assertEqual(fresh.chat_state(session_b)["chat"]["session_id"], session_b)
            # 未知会话：明确报错，绝不静默回落
            with self.assertRaises(WorkbenchFlowError):
                flow.chat_send_start("任意", session_id="deadbeef" * 4)

    def test_chat_history_migrates_once_to_user_level(self):
        """聊天历史用户级迁移：旧仓库级 workbench/chat 首次加载即复制到
        用户级（同 ID 不覆盖、原文件保留、幂等、0600）。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legacy_dir = root / "workbench" / "chat"
            legacy_dir.mkdir(parents=True)
            legacy_id = "a" * 32
            (legacy_dir / f"{legacy_id}.json").write_text(json.dumps({
                "schema": "creative-chat/1",
                "session_id": legacy_id,
                "created_at": "2026-10-01T10:00:00+08:00",
                "updated_at": "2026-10-01T10:00:00+08:00",
                "turns": [{"turn_id": "t1", "role": "user", "content": "旧会话内容", "created_at": "2026-10-01T10:00:00+08:00"}],
                "drafts": [],
            }, ensure_ascii=False), encoding="utf-8")
            store = CreativeChatStore(root)
            user_path = store.directory / f"{legacy_id}.json"
            self.assertTrue(user_path.is_file())
            self.assertEqual(user_path.stat().st_mode & 0o777, 0o600)
            self.assertTrue((legacy_dir / f"{legacy_id}.json").is_file())  # 原文件保留
            # 幂等：再建一个 store 不破坏、不重复
            store2 = CreativeChatStore(root)
            self.assertEqual(
                store2.list_sessions()[0]["session_id"], legacy_id,
            )
            # 用户级已有同名会话时绝不覆盖（用户级是唯一真源）
            user_path.write_text(json.dumps({"schema": "creative-chat/1",
                "session_id": legacy_id, "created_at": "", "updated_at": "2026-10-02T00:00:00+08:00",
                "turns": [], "drafts": []}, ensure_ascii=False), encoding="utf-8")
            CreativeChatStore(root)
            self.assertEqual(CreativeChatStore(root).list_sessions()[0]["turns"], 0)

    def test_corrupt_chat_files_do_not_break_other_sessions(self):
        """B7（review 5630859051）：单个损坏 JSON 绝不拖垮其他会话 ——
        迁移/列表/最近会话逐文件跳过损坏件、原件零改动、历史目录 0700、
        显式选中损坏会话如实报错而其他会话照常加载。"""
        import os
        import stat as stat_module

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def session(sid, content, updated):
                return {
                    "schema": "creative-chat/1",
                    "session_id": sid,
                    "created_at": updated,
                    "updated_at": updated,
                    "turns": [{"turn_id": "t1", "role": "user",
                               "content": content, "created_at": updated}],
                    "drafts": [],
                }

            # ── 1) 仓库级：一个损坏 + 两个有效 → 初始化/迁移成功 ──
            legacy = root / "workbench" / "chat"
            legacy.mkdir(parents=True)
            valid_a_id, valid_b_id, corrupt_id = "a" * 32, "c" * 32, "b" * 32
            (legacy / f"{valid_a_id}.json").write_text(json.dumps(
                session(valid_a_id, "有效甲", "2026-10-01T10:00:00+08:00"),
                ensure_ascii=False), encoding="utf-8")
            (legacy / f"{valid_b_id}.json").write_text(json.dumps(
                session(valid_b_id, "有效乙", "2026-10-01T11:00:00+08:00"),
                ensure_ascii=False), encoding="utf-8")
            corrupt_legacy_path = legacy / f"{corrupt_id}.json"
            corrupt_text = '{"schema": "creative-chat/1", "session_id": "' + corrupt_id + '", "trun'
            corrupt_legacy_path.write_text(corrupt_text, encoding="utf-8")

            store = CreativeChatStore(root)  # 此前：损坏件会让 __init__ 直接失败
            # 历史目录显式私有 0700（文件 0600 之上）
            self.assertEqual(
                stat_module.S_IMODE(store.directory.stat().st_mode), 0o700,
            )
            # 有效件迁移成功；损坏件被跳过且仓库原件逐字节保留
            self.assertTrue((store.directory / f"{valid_a_id}.json").is_file())
            self.assertTrue((store.directory / f"{valid_b_id}.json").is_file())
            self.assertFalse((store.directory / f"{corrupt_id}.json").exists())
            self.assertEqual(
                corrupt_legacy_path.read_text(encoding="utf-8"), corrupt_text,
            )

            # ── 2) 用户级：一个损坏（mtime 最新）+ 两个有效 → 只含有效件 ──
            corrupt_user_id = "d" * 32
            corrupt_user_path = store.directory / f"{corrupt_user_id}.json"
            corrupt_user_text = '{"schema": "creative-chat/1", "broken'
            corrupt_user_path.write_text(corrupt_user_text, encoding="utf-8")
            # 固定 mtime（不依赖迁移拷贝的创建时序）：损坏件最新 → 证明被跳过
            os.utime(store.directory / f"{valid_a_id}.json", (1_000_000, 1_000_000))
            os.utime(store.directory / f"{valid_b_id}.json", (2_000_000, 2_000_000))
            os.utime(corrupt_user_path, (3_000_000, 3_000_000))

            sessions = store.list_sessions()
            self.assertEqual({s["session_id"] for s in sessions},
                             {valid_a_id, valid_b_id})
            self.assertEqual(sessions[0]["session_id"], valid_b_id)  # 按最近更新倒序
            # 最近会话跳过「最新但损坏」的件，返回最近的「有效」会话
            self.assertEqual(store.load_latest()["session_id"], valid_b_id)
            # 显式选中有效会话照常精确加载；选中损坏会话如实报错且不影响其他
            self.assertEqual(store.load(valid_a_id)["session_id"], valid_a_id)
            with self.assertRaises(CreativeChatError):
                store.load(corrupt_user_id)
            self.assertEqual(store.load_latest()["session_id"], valid_b_id)

            # ── 3) 幂等/零丢失：重建 store 后一切不变、损坏件绝不自动删除 ──
            store2 = CreativeChatStore(root)
            self.assertEqual({s["session_id"] for s in store2.list_sessions()},
                              {valid_a_id, valid_b_id})
            self.assertEqual(
                stat_module.S_IMODE(store2.directory.stat().st_mode), 0o700,
            )
            self.assertEqual(
                corrupt_legacy_path.read_text(encoding="utf-8"), corrupt_text,
            )
            self.assertEqual(
                corrupt_user_path.read_text(encoding="utf-8"), corrupt_user_text,
            )
            self.assertEqual(
                len(list(store2.directory.glob("*.json"))), 3,
            )  # 2 有效迁移 + 1 损坏保留：绝不自动删除任何原件

    def test_loopback_endpoint_is_labeled_fixture_even_without_injected_provider(self):
        """诚实标注：即使未注入 provider_factory，指向 loopback 的 Chat 端点
        也必须标记为本地夹具，绝不冒充真实模型连接。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "chat",
                "chat_base_url": "http://127.0.0.1:9999/v1",
                "model": "mock-e2e-model",
                "api_key": "sk-loopback",
            }))
            llm = StreamChatLLM(["内容"], [])
            flow = WorkbenchFlow(root, provider_factory=lambda settings: llm)
            flow.connection_kind = "real"  # 模拟未注入夹具的真实模式
            context = flow.chat_send_start("loopback 端点")
            self.assertEqual(context["provider_kind"], "fixture")
            # 官方端点则是真实连接
            save_settings(root, apply_settings_update(load_settings(root), {
                "provider_mode": "deepseek",
                "api_key": "sk-real-endpoint",
            }))
            context2 = flow.chat_send_start("官方端点")
            self.assertEqual(context2["provider_kind"], "real")

    def test_interleaved_replies_reload_latest_and_lose_no_turns(self):
        """Nexus B2 (5626927896)：两个交错开启的流式回复无论以什么顺序完成，
        已保存的 turns 绝不丢失 —— 完成时锁内 re-load 最新会话再追加，
        不允许任何一方用陈旧内存快照整体覆盖存储。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["A 的回复"], []))
            self._configure(root)
            context_a = flow.chat_send_start("消息 A")
            context_b = flow.chat_send_start("消息 B")
            # 交错完成：B 先完成、A 后完成（A 持有的是最旧的会话快照）
            list(flow.chat_stream_reply(context_b))
            list(flow.chat_stream_reply(context_a))
            reloaded = WorkbenchFlow(root, provider_factory=lambda s: None).chat_state()["chat"]
            self.assertEqual([t["role"] for t in reloaded["turns"]],
                             ["user", "user", "assistant", "assistant"])
            self.assertEqual([t["content"] for t in reloaded["turns"]],
                             ["消息 A", "消息 B", "A 的回复", "A 的回复"])

    def test_concurrent_draft_edit_during_stream_is_never_overwritten(self):
        """Nexus B2：流式回复进行中发生的草稿编辑，在回复完成持久化后仍
        完整保留 —— 助手 turn 追加走锁内 re-load，绝不覆盖并发保存的数据。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["流式回复正文"], []))
            self._configure(root)
            context = flow.chat_send_start("会话消息")
            list(flow.chat_stream_reply(context))
            flow.chat_draft_generate()
            context2 = flow.chat_send_start("第二条消息")
            events = flow.chat_stream_reply(context2)
            next(events)  # 流式进行中……
            # 并发路径：流式未完成时保存草稿编辑（旧实现会整体覆盖它）
            flow.chat_draft_save("流式进行中的并发草稿编辑")
            rest = list(events)
            self.assertTrue(any(e["type"] == "done" for e in rest))
            reloaded = WorkbenchFlow(root, provider_factory=lambda s: None).chat_state()["chat"]
            self.assertEqual([d["content"] for d in reloaded["drafts"]],
                             ["流式回复正文", "流式进行中的并发草稿编辑"])
            self.assertEqual([t["role"] for t in reloaded["turns"]],
                             ["user", "assistant", "user", "assistant"])

    def test_retry_after_stop_reuses_user_turn_without_duplicating(self):
        """Nexus B3：停止后的重发按 turn id 幂等复用已保存的 user turn，
        绝不追加重复的用户消息；完成后一问一答，无重复计费调用。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, calls = self._flow(root, StreamChatLLM(["重发后的完整回复"], []))
            self._configure(root)
            context = flow.chat_send_start("聊一半就停的消息")
            turn_id = context["user_turn"]["turn_id"]
            events = flow.chat_stream_reply(context)
            next(events)
            events.close()  # 用户停止：user turn 已保存、无 assistant 回复
            chat = flow.chat_state()["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user"])
            # 幂等重试：复用同一条 user turn（id 相同），线程不出现第二条 user
            retry_context = flow.chat_send_start(
                "聊一半就停的消息", [], retry_turn_id=turn_id
            )
            self.assertEqual(retry_context["user_turn"]["turn_id"], turn_id)
            chat = flow.chat_state()["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user"])
            self.assertEqual([t["content"] for t in chat["turns"]], ["聊一半就停的消息"])
            list(flow.chat_stream_reply(retry_context))
            reloaded = WorkbenchFlow(root, provider_factory=lambda s: None).chat_state()["chat"]
            self.assertEqual([t["role"] for t in reloaded["turns"]], ["user", "assistant"])
            self.assertEqual([t["content"] for t in reloaded["turns"]],
                             ["聊一半就停的消息", "重发后的完整回复"])
            # 两次模型调用都是显式用户动作（首次 + 重发），零隐藏第三次
            self.assertEqual(len(calls), 2)

    def test_retry_is_rejected_when_turn_already_replied_or_unknown(self):
        """Nexus B3：重发只针对「仍是最后一条且尚无回复」的 user turn；
        已有回复或不匹配的 id 一律拒绝且零模型调用，状态保持不变。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, calls = self._flow(root, StreamChatLLM(["回复"], []))
            self._configure(root)
            context = flow.chat_send_start("已有回复的消息")
            turn_id = context["user_turn"]["turn_id"]
            list(flow.chat_stream_reply(context))
            with self.assertRaises(WorkbenchFlowError) as ctx:
                flow.chat_send_start("已有回复的消息", [], retry_turn_id=turn_id)
            self.assertIn("状态已变化", str(ctx.exception))
            with self.assertRaises(WorkbenchFlowError):
                flow.chat_send_start("任意内容", [], retry_turn_id="t999")
            self.assertEqual(len(calls), 1)  # 拒绝路径零模型调用
            chat = flow.chat_state()["chat"]
            self.assertEqual([t["role"] for t in chat["turns"]], ["user", "assistant"])

    def test_draft_provider_kind_survives_reload(self):
        """Nexus B4：草稿来源标注（fixture/real）随 revision 原子持久化，
        重载后不消失 —— 绝不在 append 之后才在内存里补字段。"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            flow, _ = self._flow(root, StreamChatLLM(["草稿内容"], []))
            self._configure(root)
            context = flow.chat_send_start("选题讨论")
            list(flow.chat_stream_reply(context))
            generated = flow.chat_draft_generate()["draft"]
            self.assertEqual(generated["provider_kind"], "fixture")
            flow.chat_draft_save("用户编辑版")
            reloaded = WorkbenchFlow(root, provider_factory=lambda s: None).chat_state()["chat"]
            # 模型整理的 revision 带持久化来源；用户编辑版无模型来源标注
            self.assertEqual([d.get("provider_kind") for d in reloaded["drafts"]],
                             ["fixture", ""])


class TopicFirstChatTests(_UserSettingsIsolatedTestCase):
    """Issue #29 选题驱动创作（issuecomment-6369945828）：任务意图识别 →
    有界公开来源检索 → 透明检索播报 + 证据注入；聊聊模式零检索；
    检索失败/未接线时诚实记录「未联网核实」，绝不阻断消息发送。"""

    class CapturingLLM:
        """捕获完整 messages（含注入的检索上下文）的离线流式夹具。"""

        def __init__(self, chunks):
            self.chunks = list(chunks)
            self.seen = []

        def chat_stream(self, messages):
            self.seen.append([dict(m) for m in messages])
            for chunk in self.chunks:
                yield chunk

    def _flow(self, root, llm, topic_search=None):
        return WorkbenchFlow(
            root,
            provider_factory=lambda settings: llm,
            topic_search=topic_search,
        )

    def _configure(self, root):
        save_settings(root, apply_settings_update(load_settings(root), {
            "provider_mode": "deepseek",
            "api_key": "sk-chat-fixture",
        }))

    def test_video_task_topic_extraction(self):
        """确定性意图识别与主题提取：命中任务标记才提取，零模型调用；
        聊聊模式与无主题任务绝不硬造主题（真实模糊处才反问）。"""

        cases = [
            ("我想就王扁被打做个视频", "王扁被打"),
            ("我想就《王扁被打》做个视频", "王扁被打"),
            ("帮我做一期关于AI取代程序员的视频", "AI取代程序员"),
            ("给我做个视频讲王扁被打", "王扁被打"),
            ("「王扁被打」这个事，出个视频吧", "王扁被打"),
            ("请帮我拍个视频：深夜自习室", "深夜自习室"),
            ("做个视频", ""),
            ("就是做个视频", ""),
            ("王扁被打最近很火，我想聊聊", ""),
            ("你好，想聊聊夜间城市选题", ""),
        ]
        for text, expected in cases:
            self.assertEqual(WorkbenchFlow._video_task_topic(text), expected, text)

    def test_task_message_triggers_bounded_search_and_injects_sources(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            searches = []

            def topic_search(topic):
                searches.append(topic)
                return {
                    "status": "ok",
                    "query": topic,
                    "sources": [{
                        "title": "王扁被打事件梳理",
                        "uploader": "时事观察",
                        "published_at": "2026-10-19",
                        "url": "https://www.bilibili.com/video/BV1fixture01",
                        "description": "封面新闻报道梳理",
                    }],
                }

            llm = self.CapturingLLM(["好的", "，这是起步产出。"])
            flow = self._flow(root, llm, topic_search=topic_search)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            # 有界检索恰好一次、主题正确；返回快照带证据
            self.assertEqual(searches, ["王扁被打"])
            discovery = context["session"].get("topic_discovery")
            self.assertEqual(discovery["status"], "ok")
            self.assertEqual(discovery["turn_id"], context["user_turn"]["turn_id"])
            self.assertEqual(discovery["sources"][0]["url"],
                             "https://www.bilibili.com/video/BV1fixture01")
            events = list(flow.chat_stream_reply(context))
            # 透明检索播报在任何 delta 之前
            self.assertEqual(events[0]["type"], "search")
            self.assertEqual(events[0]["query"], "王扁被打")
            self.assertEqual(events[0]["status"], "ok")
            self.assertEqual(events[0]["count"], 1)
            self.assertEqual(events[1]["type"], "delta")
            self.assertEqual(llm.seen, [])  # Owner UX: no title-only automatic script charge.
            flow.chat_draft_generate(context["session"]["session_id"], mode="topic_only")
            messages = llm.seen[0]
            evidence = next(m for m in messages if "【主动检索来源】" in m["content"])
            self.assertIn("BV1fixture01", evidence["content"])
            self.assertIn("不是权威事实核查", evidence["content"])
            self.assertIn("未分析参考视频", str(messages))

    def test_search_is_idempotent_within_session(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            searches = []

            def topic_search(topic):
                searches.append(topic)
                return {
                    "status": "ok",
                    "query": topic,
                    "sources": [{
                        "title": "来源A", "uploader": "u", "published_at": "2026",
                        "url": "https://www.bilibili.com/video/BV1fixture01",
                        "description": "d",
                    }],
                }

            llm = self.CapturingLLM(["第一轮", "回复", "第二轮", "回复"])
            flow = self._flow(root, llm, topic_search=topic_search)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            session_id = context["session"]["session_id"]
            list(flow.chat_stream_reply(context))
            # 同会话第二条任务消息：不再检索（幂等）、不再播报、不重复注入
            context2 = flow.chat_send_start("再就王扁被打做个视频", session_id=session_id)
            self.assertEqual(searches, ["王扁被打"])
            events2 = list(flow.chat_stream_reply(context2))
            self.assertEqual([e for e in events2 if e["type"] == "search"], [])
            self.assertEqual(llm.seen, [])
            self.assertEqual(len(flow.creative.load(session_id)["turns"]), 4)

    def test_chat_mode_never_triggers_search(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            searches = []

            def topic_search(topic):
                searches.append(topic)
                return {"status": "ok", "query": topic, "sources": []}

            llm = self.CapturingLLM(["聊聊吧"])
            flow = self._flow(root, llm, topic_search=topic_search)
            self._configure(root)
            context = flow.chat_send_start("王扁被打最近很火，我想聊聊")
            self.assertEqual(searches, [])
            self.assertIsNone(context["session"].get("topic_discovery"))
            events = list(flow.chat_stream_reply(context))
            self.assertEqual([e for e in events if e["type"] == "search"], [])
            self.assertEqual(len(llm.seen[0]), 2)  # system + user，无注入

    def test_unwired_search_records_unavailable_and_stays_honest(self):
        """topic_search=None：消息照常发送，证据记录 unavailable，
        stream 播报「未联网核实」，模型上下文拿到诚实声明 ——
        无检索能力绝不假装做过研究。"""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            llm = self.CapturingLLM(["基于未核实信息的构思"])
            flow = self._flow(root, llm, topic_search=None)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            discovery = context["session"].get("topic_discovery")
            self.assertEqual(discovery["status"], "unavailable")
            self.assertEqual(discovery["turn_id"], context["user_turn"]["turn_id"])
            events = list(flow.chat_stream_reply(context))
            search_events = [e for e in events if e["type"] == "search"]
            self.assertEqual(len(search_events), 1)
            self.assertEqual(search_events[0]["status"], "unavailable")
            self.assertEqual(llm.seen, [])
            flow.chat_draft_generate(context["session"]["session_id"], mode="topic_only")
            self.assertIn("未联网核实", str(llm.seen[0]))

    def test_search_callback_failure_never_blocks_send(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def broken(topic):
                raise RuntimeError("网络故障")

            llm = self.CapturingLLM(["回复"])
            flow = self._flow(root, llm, topic_search=broken)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            self.assertEqual(
                context["session"]["topic_discovery"]["status"], "unavailable"
            )

    def test_empty_search_result_is_unavailable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def empty(topic):
                return {"status": "ok", "query": topic, "sources": []}

            llm = self.CapturingLLM(["回复"])
            flow = self._flow(root, llm, topic_search=empty)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            discovery = context["session"]["topic_discovery"]
            self.assertEqual(discovery["status"], "unavailable")
            self.assertIn("没有返回", discovery["note"])

    def test_draft_generate_injects_discovery_context(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def topic_search(topic):
                return {
                    "status": "ok",
                    "query": topic,
                    "sources": [{
                        "title": "来源A", "uploader": "u", "published_at": "2026",
                        "url": "https://www.bilibili.com/video/BV1fixture01",
                        "description": "d",
                    }],
                }

            llm = self.CapturingLLM(["聊天回复", "草稿正文"])
            flow = self._flow(root, llm, topic_search=topic_search)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            list(flow.chat_stream_reply(context))
            result = flow.chat_draft_generate(mode="topic_only")
            self.assertEqual(result["draft"]["revision"], 1)
            # 草稿上下文：DRAFT prompt + 会话证据 + 完整历史
            draft_messages = llm.seen[-1]
            self.assertEqual(draft_messages[0]["role"], "system")
            self.assertIn("参考来源", draft_messages[0]["content"])
            self.assertIn("【主动检索来源】", str(draft_messages))
            self.assertEqual([m["role"] for m in draft_messages if m["role"] != "system"], ["user", "assistant"])

    def test_discovery_persists_across_reload(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            def topic_search(topic):
                return {
                    "status": "ok",
                    "query": topic,
                    "sources": [{
                        "title": "来源A", "uploader": "u", "published_at": "2026",
                        "url": "https://www.bilibili.com/video/BV1fixture01",
                        "description": "d",
                    }],
                }

            llm = self.CapturingLLM(["回复"])
            flow = self._flow(root, llm, topic_search=topic_search)
            self._configure(root)
            context = flow.chat_send_start("我想就王扁被打做个视频")
            session_id = context["session"]["session_id"]
            list(flow.chat_stream_reply(context))
            # 刷新精确恢复：新 flow 实例读同一存储，检索证据不丢
            reloaded = WorkbenchFlow(
                root, provider_factory=lambda s: None
            ).chat_state(session_id)["chat"]
            discovery = reloaded["topic_discovery"]
            self.assertEqual(discovery["status"], "ok")
            self.assertEqual(discovery["sources"][0]["url"],
                             "https://www.bilibili.com/video/BV1fixture01")

    def test_set_discovery_per_topic_first_write_wins(self):
        with tempfile.TemporaryDirectory() as raw:
            from deeptalk_studio.workbench.creative_chat import CreativeChatStore

            root = Path(raw)
            store = CreativeChatStore(root)
            session = store.new_session()
            sid = session["session_id"]
            first = store.set_discovery(
                sid, {"query": "q", "status": "ok", "sources": [], "turn_id": "t1"}
            )
            second = store.set_discovery(
                sid, {"query": "q", "status": "unavailable", "turn_id": "t9"}
            )
            self.assertTrue(first)
            self.assertFalse(second)
            data = store.load(sid)
            self.assertEqual(data["topic_discovery"]["status"], "ok")
            self.assertEqual(data["topic_discovery"]["turn_id"], "t1")
            with self.assertRaises(Exception):
                store.set_discovery("nonexistent00", {"query": "q"})


if __name__ == "__main__":
    unittest.main()
