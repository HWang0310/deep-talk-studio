"""Read-only Finished Cut review and episode-bound production feedback.

This module intentionally has no video-render, NLE-project, cut-list, or media
mutation API. It compares a creator's finished cut with the prior Asset Pack,
then records conservative episode observations for later human product review.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Sequence


class FinishedCutReviewError(ValueError):
    """The read-only review cannot safely establish its evidence lineage."""


OBSERVATION_STATUSES = {"USED", "NOT_USED", "UNKNOWN"}
PRESENTATIONS = {"full_screen", "overlay", "PIP", "crop", "partial_use", "extended", "UNKNOWN"}
USAGE_MODES = {"full", "shortened", "extended", "UNKNOWN"}
MATCH_THRESHOLD = Decimal("0.080")
MIN_DISCRIMINATIVE_SPREAD = Decimal("0.006")
FINGERPRINT_FPS = 2
FINGERPRINT_WIDTH = 32
FINGERPRINT_HEIGHT = 18
_FRAME_BYTES = FINGERPRINT_WIDTH * FINGERPRINT_HEIGHT


@dataclass(frozen=True)
class FinishedCutFeedbackPaths:
    review_json: Path
    feedback_json: Path
    review_markdown: Path
    asset_pack_markdown: Path

    def __getitem__(self, name: str) -> Path:
        return getattr(self, name)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_digest(value: object, label: str) -> str:
    text = str(value or "")
    if len(text) != 64:
        raise FinishedCutReviewError(f"{label} 缺少 64 位 digest")
    return text


def _number(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise FinishedCutReviewError(f"{label} 不是合法时间") from error
    if result < 0:
        raise FinishedCutReviewError(f"{label} 不能为负数")
    return result


def _format_number(value: Decimal) -> str:
    rendered = format(value.quantize(Decimal("0.001")), "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _digest(mapping: Mapping, field: str) -> str:
    payload = dict(mapping)
    payload.pop(field, None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_inputs(edit_map: Mapping, manifest: Mapping, finished_cut: Mapping) -> None:
    if edit_map.get("artifact_version") != "edit-map/1":
        raise FinishedCutReviewError("Finished Cut Review 只接受 edit-map/1")
    if manifest.get("artifact_version") != "visual-asset-manifest/1":
        raise FinishedCutReviewError("Finished Cut Review 只接受 visual-asset-manifest/1")
    if edit_map.get("asset_manifest_digest") != manifest.get("manifest_digest"):
        raise FinishedCutReviewError("Edit Map 与 Asset Manifest lineage 不一致")
    _require_digest(edit_map.get("map_digest"), "Edit Map")
    _require_digest(manifest.get("manifest_digest"), "Asset Manifest")
    _require_digest(finished_cut.get("sha256"), "Finished Cut")
    _number(finished_cut.get("duration_seconds"), "Finished Cut 时长")
    if not isinstance(edit_map.get("rows"), list):
        raise FinishedCutReviewError("Edit Map 缺少 rows")


def _observation_index(observations: Sequence[Mapping], manifest_assets: Sequence[Mapping]) -> dict[str, Mapping]:
    allowed_assets = {str(item.get("filename", "")) for item in manifest_assets}
    indexed: dict[str, Mapping] = {}
    for item in observations:
        filename = str(item.get("asset_filename", ""))
        if filename not in allowed_assets:
            raise FinishedCutReviewError("实际观察引用了 Asset Manifest 之外的素材")
        if filename in indexed:
            raise FinishedCutReviewError("同一素材不能有两条相互竞争的实际观察")
        status = str(item.get("status", ""))
        if status not in OBSERVATION_STATUSES:
            raise FinishedCutReviewError("实际素材状态无效")
        presentation = str(item.get("presentation", "UNKNOWN"))
        if presentation not in PRESENTATIONS:
            raise FinishedCutReviewError("实际呈现方式无效")
        usage_mode = str(item.get("usage_mode", "UNKNOWN"))
        if usage_mode not in USAGE_MODES:
            raise FinishedCutReviewError("实际使用长度状态无效")
        if status == "USED":
            start = _number(item.get("actual_start_seconds"), "实际开始时间")
            end = _number(item.get("actual_end_seconds"), "实际结束时间")
            if end <= start:
                raise FinishedCutReviewError("实际素材结束时间必须晚于开始时间")
        elif item.get("actual_start_seconds") is not None or item.get("actual_end_seconds") is not None:
            raise FinishedCutReviewError("非 USED 素材不能伪造实际时间")
        if not str(item.get("evidence", "")).strip():
            raise FinishedCutReviewError("实际观察必须保留 evidence")
        indexed[filename] = item
    return indexed


def _planned_vs_actual(edit_map: Mapping, manifest: Mapping, finished_cut: Mapping, observations: Sequence[Mapping]) -> tuple[list[dict], list[dict]]:
    observed = _observation_index(observations, manifest.get("assets", []))
    duration = _number(finished_cut["duration_seconds"], "Finished Cut 时长")
    rows: list[dict] = []
    overrides: list[dict] = []
    for planned in edit_map["rows"]:
        start = _number(planned.get("actual_start_seconds"), "计划开始时间")
        end = _number(planned.get("actual_end_seconds"), "计划结束时间")
        if end <= start:
            raise FinishedCutReviewError("计划时间必须单调")
        filename = str(planned.get("asset_filename", ""))
        row = {
            "sequence": int(planned.get("sequence", len(rows) + 1)),
            "span_id": str(planned.get("span_id", "")),
            "planned_start_seconds": _format_number(start),
            "planned_end_seconds": _format_number(end),
            "planned_decision": str(planned.get("decision", "KEEP_A_ROLL")),
            "planned_asset_filename": filename,
            "planned_placement_advice": str(planned.get("placement_advice", "")),
            "spoken_summary": str(planned.get("spoken_summary", "")),
            "actual_status": "NOT_APPLICABLE" if not filename else "UNKNOWN",
            "actual_start_seconds": None,
            "actual_end_seconds": None,
            "timing_offset_seconds": None,
            "actual_presentation": "KEEP_A_ROLL" if not filename else "UNKNOWN",
            "actual_usage_mode": "NOT_APPLICABLE" if not filename else "UNKNOWN",
            "actual_evidence": "KEEP_A_ROLL 是正式计划，不对应独立资产。" if not filename else "没有足够证据判断该素材是否在成片中采用。",
        }
        if filename and filename in observed:
            item = observed[filename]
            status = str(item["status"])
            row["actual_status"] = status
            row["actual_presentation"] = str(item.get("presentation", "UNKNOWN"))
            row["actual_usage_mode"] = str(item.get("usage_mode", "UNKNOWN"))
            row["actual_evidence"] = str(item["evidence"])
            if status == "USED":
                actual_start = _number(item["actual_start_seconds"], "实际开始时间")
                actual_end = _number(item["actual_end_seconds"], "实际结束时间")
                if actual_end > duration:
                    raise FinishedCutReviewError("实际素材时间超出 Finished Cut 时长")
                row["actual_start_seconds"] = _format_number(actual_start)
                row["actual_end_seconds"] = _format_number(actual_end)
                row["timing_offset_seconds"] = _format_number(actual_start - start)
                if actual_start != start or actual_end != end or row["actual_presentation"] != "full_screen":
                    overrides.append({
                        "classification": "USER_EDIT_OBSERVATION",
                        "asset_filename": filename,
                        "planned_start_seconds": _format_number(start),
                        "planned_end_seconds": _format_number(end),
                        "actual_start_seconds": _format_number(actual_start),
                        "actual_end_seconds": _format_number(actual_end),
                        "actual_presentation": row["actual_presentation"],
                        "actual_usage_mode": row["actual_usage_mode"],
                        "evidence": row["actual_evidence"],
                    })
        rows.append(row)
    return rows, overrides


def build_finished_cut_review(
    edit_map: Mapping,
    manifest: Mapping,
    finished_cut: Mapping,
    observations: Sequence[Mapping],
    *,
    episode_observations: Sequence[Mapping] = (),
) -> Mapping:
    """Build a lineage-bound comparison without changing any media or plan."""
    _validate_inputs(edit_map, manifest, finished_cut)
    comparison, overrides = _planned_vs_actual(edit_map, manifest, finished_cut, observations)
    review = {
        "artifact_version": "finished-cut-review/1",
        "review_mode": "read_only",
        "finished_cut": dict(finished_cut),
        "edit_map_digest": str(edit_map["map_digest"]),
        "asset_manifest_digest": str(manifest["manifest_digest"]),
        "planned_vs_actual": comparison,
        "creator_override_observations": overrides,
        "episode_observations": [dict(item) for item in episode_observations],
        "limitations": [
            "成片复盘只比较计划与实际素材使用，不修改成片或剪映工程。",
            "没有达到匹配阈值的素材使用状态必须保留为 UNKNOWN。",
            "本工件不预测播放量、爆款概率或创作者审美得分。",
        ],
    }
    review["review_digest"] = _digest(review, "review_digest")
    return review


def build_production_feedback(review: Mapping) -> Mapping:
    """Turn episode observations into reviewable candidates, never global rules."""
    if review.get("artifact_version") != "finished-cut-review/1":
        raise FinishedCutReviewError("Production Feedback 只接受 finished-cut-review/1")
    if _digest(review, "review_digest") != review.get("review_digest"):
        raise FinishedCutReviewError("Finished Cut Review digest 不一致")
    candidates = []
    for observation in review.get("episode_observations", []):
        candidates.append({
            "rule_status": "CANDIDATE_PRODUCT_RULE",
            "category": str(observation.get("category", "production_feedback")),
            "proposed_product_change": str(observation.get("proposed_product_change") or observation.get("finding", "")),
            "confidence": str(observation.get("confidence", "low")),
            "evidence_episode": str(observation.get("evidence_episode", "")),
            "requires_human_or_multi_episode_review": True,
        })
    feedback = {
        "artifact_version": "production-feedback/1",
        "review_digest": str(review["review_digest"]),
        "finished_cut_sha256": str(review["finished_cut"]["sha256"]),
        "episode_observations": list(review.get("episode_observations", [])),
        "creator_override_observations": list(review.get("creator_override_observations", [])),
        "candidate_product_rules": candidates,
        "limitations": ["单一 Episode 的反馈不得自动升级为全局产品规则。"],
    }
    feedback["feedback_digest"] = _digest(feedback, "feedback_digest")
    return feedback


def _run_json(command: Sequence[str], error_message: str) -> Mapping:
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.returncode != 0:
        raise FinishedCutReviewError(error_message)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise FinishedCutReviewError(error_message) from error


def inspect_finished_cut_media(path: Path) -> Mapping:
    """Probe media through ffprobe without writing beside or into the source file."""
    source = Path(path).resolve()
    if not source.is_file():
        raise FinishedCutReviewError("Finished Cut 文件不存在")
    data = _run_json(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name", "-show_entries", "stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels", "-of", "json", str(source)],
        "Finished Cut 无法通过 ffprobe 读取",
    )
    streams = list(data.get("streams", []))
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video is None or audio is None:
        raise FinishedCutReviewError("Finished Cut 必须同时包含可读视频和音频 stream")
    duration = _number(data.get("format", {}).get("duration"), "Finished Cut 时长")
    if duration <= 0:
        raise FinishedCutReviewError("Finished Cut 时长必须大于零")
    return {
        "source_path": str(source),
        "sha256": _sha256_file(source),
        "duration_seconds": _format_number(duration),
        "format_name": str(data.get("format", {}).get("format_name", "")),
        "resolution": {"width": int(video.get("width", 0)), "height": int(video.get("height", 0))},
        "frame_rate": str(video.get("avg_frame_rate", "")),
        "streams": ["video", "audio"],
        "video_codec": str(video.get("codec_name", "")),
        "audio_codec": str(audio.get("codec_name", "")),
        "audio_sample_rate": str(audio.get("sample_rate", "")),
        "audio_channels": int(audio.get("channels", 0)),
    }


def _fingerprints(path: Path, *, start_seconds: Decimal | None = None, duration_seconds: Decimal | None = None, fps: int = FINGERPRINT_FPS) -> list[bytes]:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start_seconds is not None:
        command.extend(["-ss", _format_number(start_seconds)])
    command.extend(["-i", str(path)])
    if duration_seconds is not None:
        command.extend(["-t", _format_number(duration_seconds)])
    command.extend(["-an", "-vf", f"fps={fps},scale={FINGERPRINT_WIDTH}:{FINGERPRINT_HEIGHT}:flags=area,format=gray", "-f", "rawvideo", "-"])
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        raise FinishedCutReviewError("无法读取用于只读比对的画面帧")
    usable = len(result.stdout) - (len(result.stdout) % _FRAME_BYTES)
    return [result.stdout[index:index + _FRAME_BYTES] for index in range(0, usable, _FRAME_BYTES)]


def _frame_distance(left: bytes, right: bytes) -> float:
    return sum(abs(a - b) for a, b in zip(left, right)) / (_FRAME_BYTES * 255)


def _best_sequence_match(haystack: Sequence[bytes], needle: Sequence[bytes]) -> tuple[int, Decimal] | None:
    if not needle or len(haystack) < len(needle):
        return None
    best_start = 0
    best_score = float("inf")
    for start in range(len(haystack) - len(needle) + 1):
        score = sum(_frame_distance(haystack[start + offset], frame) for offset, frame in enumerate(needle)) / len(needle)
        if score < best_score:
            best_start, best_score = start, score
    return best_start, Decimal(str(best_score))


def sequence_is_discriminative(frames: Sequence[bytes]) -> bool:
    """Reject near-static visual sequences that cannot identify an asset safely."""
    if len(frames) < 2:
        return False
    return max(Decimal(str(_frame_distance(frames[0], frame))) for frame in frames[1:]) >= MIN_DISCRIMINATIVE_SPREAD


def match_manifest_assets(finished_cut: Path, manifest: Mapping) -> list[Mapping]:
    """Conservatively find full-frame asset use; uncertainty is explicitly UNKNOWN."""
    source = Path(finished_cut).resolve()
    media = inspect_finished_cut_media(source)
    cut_frames = _fingerprints(source)
    observations = []
    for asset in manifest.get("assets", []):
        filename = str(asset.get("filename", ""))
        local = Path(str(asset.get("local_path", "")))
        fallback = {
            "asset_filename": filename,
            "status": "UNKNOWN",
            "actual_start_seconds": None,
            "actual_end_seconds": None,
            "presentation": "UNKNOWN",
            "usage_mode": "UNKNOWN",
            "evidence": "没有足够的全画幅帧匹配证据，不能判断是否采用。",
        }
        if not filename or not local.is_file():
            fallback["evidence"] = "素材文件不可读，不能判断 Finished Cut 是否采用。"
            observations.append(fallback)
            continue
        asset_frames = _fingerprints(local)
        if not sequence_is_discriminative(asset_frames):
            fallback["evidence"] = "素材画面在低分辨率比对中缺少可区分变化，不能据相同背景宣称已采用。"
            observations.append(fallback)
            continue
        match = _best_sequence_match(cut_frames, asset_frames)
        if match is None or match[1] > MATCH_THRESHOLD:
            observations.append(fallback)
            continue
        start_index, score = match
        start = Decimal(start_index) / Decimal(FINGERPRINT_FPS)
        actual_duration = Decimal(len(asset_frames)) / Decimal(FINGERPRINT_FPS)
        end = min(start + actual_duration, _number(media["duration_seconds"], "Finished Cut 时长"))
        observations.append({
            "asset_filename": filename,
            "status": "USED",
            "actual_start_seconds": _format_number(start),
            "actual_end_seconds": _format_number(end),
            "presentation": "full_screen",
            "usage_mode": "full",
            "evidence": f"只读帧指纹完整序列匹配，采样 {FINGERPRINT_FPS}fps，归一化差异 {_format_number(score)}，阈值 {_format_number(MATCH_THRESHOLD)}。",
        })
    return observations


def _review_markdown(review: Mapping, episode_title: str) -> str:
    cut = review["finished_cut"]
    lines = [f"# 《{episode_title}》第一版成片复盘", "", "本复盘只读分析已完成的成片；不修改成片，不生成第二版，也不替用户重新剪辑。", "", "## 成片", "", f"- 时长：{cut['duration_seconds']} 秒", f"- 规格：{cut['resolution']['width']}×{cut['resolution']['height']}，{cut['frame_rate']} fps，{cut.get('video_codec', 'UNKNOWN')} / {cut.get('audio_codec', 'UNKNOWN')}", "", "## 计划 vs 实际", ""]
    for row in review["planned_vs_actual"]:
        lines.extend([f"### {row['planned_start_seconds']}–{row['planned_end_seconds']}｜{row['planned_decision']}", "", f"- 原计划素材：{row['planned_asset_filename'] or '保持人物'}", f"- 实际：{row['actual_status']}；呈现：{row['actual_presentation']}；长度使用：{row['actual_usage_mode']}", f"- 实际时间：{row['actual_start_seconds'] or 'UNKNOWN'}–{row['actual_end_seconds'] or 'UNKNOWN'}；开始偏移：{row['timing_offset_seconds'] if row['timing_offset_seconds'] is not None else 'UNKNOWN'} 秒", f"- 证据：{row['actual_evidence']}", ""])
    lines.extend(["## 边界", "", *[f"- {item}" for item in review["limitations"]], ""])
    return "\n".join(lines)


def _feedback_markdown(feedback: Mapping, episode_title: str) -> str:
    lines = [f"# 《{episode_title}》Asset Pack 使用复盘", "", "以下是本期观察和候选规则，不会自动修改未来 Episode 的产品策略。", "", "## Episode observations", ""]
    for item in feedback["episode_observations"]:
        lines.extend([f"- [{item.get('category', 'production_feedback')}] {item.get('finding', '')}（信心：{item.get('confidence', 'low')}）"])
    if not feedback["episode_observations"]:
        lines.append("- 本次尚未记录需要升级的 Episode observation。")
    lines.extend(["", "## Candidate product rules", ""])
    for item in feedback["candidate_product_rules"]:
        lines.append(f"- {item['proposed_product_change']}（{item['rule_status']}；需人工或多 Episode Review）")
    if not feedback["candidate_product_rules"]:
        lines.append("- 暂无。")
    lines.append("")
    return "\n".join(lines)


def write_finished_cut_feedback(episode_root: Path, review: Mapping, feedback: Mapping, *, episode_title: str) -> FinishedCutFeedbackPaths:
    """Write JSON/Markdown review records only; media files are never write targets."""
    if review.get("artifact_version") != "finished-cut-review/1" or feedback.get("artifact_version") != "production-feedback/1":
        raise FinishedCutReviewError("只能写入已验证的 Finished Cut Review 与 Production Feedback")
    if _digest(review, "review_digest") != review.get("review_digest"):
        raise FinishedCutReviewError("Finished Cut Review digest 不一致")
    if feedback.get("review_digest") != review.get("review_digest"):
        raise FinishedCutReviewError("Production Feedback 未绑定当前 Finished Cut Review")
    if _digest(feedback, "feedback_digest") != feedback.get("feedback_digest"):
        raise FinishedCutReviewError("Production Feedback digest 不一致")
    root = Path(episode_root).resolve()
    record_dir = root / "_DeepTalk记录"
    finished_dir = root / "10_成片"
    record_dir.mkdir(parents=True, exist_ok=True)
    finished_dir.mkdir(parents=True, exist_ok=True)
    review_json = record_dir / "finished-cut-review-r0001.json"
    feedback_json = record_dir / "production-feedback-r0001.json"
    review_markdown = finished_dir / f"《{episode_title}》第一版成片复盘.md"
    asset_pack_markdown = finished_dir / f"《{episode_title}》Asset Pack 使用复盘.md"
    review_json.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    feedback_json.write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    review_markdown.write_text(_review_markdown(review, episode_title), encoding="utf-8")
    asset_pack_markdown.write_text(_feedback_markdown(feedback, episode_title), encoding="utf-8")
    return FinishedCutFeedbackPaths(review_json, feedback_json, review_markdown, asset_pack_markdown)
