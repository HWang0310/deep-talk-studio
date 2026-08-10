# V0.3.1 Topic Discovery 真实评测

## 方法

每次评测都使用当前公开 Web Search，实际打开每条准备作为 Source Seed 的页面，并由后台 inspection manifest 记录 URL、打开引用和时间。完整 Candidate Set、网页笔记和原始链接保存在被 Git 忽略的 `discoveries/evaluations/`，公开仓库只保存去内容化汇总，避免把未经编辑判断的热点长期公开。

检查项：Raw Candidate 最小池、manifest-backed Source Seed、研究方向独立性、时间、匿名/纯传言排除、相同事件去重、先多样后补位、评分理由、首选与第 5 名排序、高风险弱证据降为 `watch`、无 Creator/engagement 数据时不造数，以及只回复编号形成 Research Handoff。每项结果必须标为 `pass`、`fail` 或 `not_applicable`，候选不足时不得推断 Top 5 表现。

## V0.3.1 执行记录

执行日期：2026-08-10。评测入口分别为：

1. Broad：“今天有什么值得讲？”
2. Tech / Business：“最近科技商业有什么值得讲？”
3. Social / Public：“最近社会公共事件有什么值得讲？”

本次 Broad 和 Tech / Business 都使用实际打开的近期公开材料及独立机构背景入口。Broad 形成 7 个 Raw Candidate、5 个不重复展示题，第一名机器分高于第五名；类别第一轮保持多样，第二轮用科技题补足空位。Tech / Business 也形成 5 个展示题。材料只被当作研究入口，不把预印本或机构表述称为定论。Social / Public 搜索后只有 1 个可用 Raw Candidate，系统因不足 7 项拒绝生成 Candidate Set；该场景的 Top 5、首选与编号交接均标为不适用，而不是伪造完整列表。

Broad 与 Tech / Business 均验证了 Candidate Set 的历史保存和 Markdown 短卡片；Broad 场景还实际执行了 `研究 1` 的编号选择，生成 Research Handoff。Handoff 仅传递研究问题、风险和入口，没有把 Seed 描述提升为已确认事实。Creator signal 在本轮没有作为必须数据；没有记录或编造播放量、搜索指数或其他 engagement 数字。

去内容化汇总见 `evaluations/v0.3.1-summary.json`。若后续改变时间窗口、评分、Preflight、去重或渲染规则，必须重新运行以上三类评测，不得用固定示例替代真实网页检查。
