# V0.3 Topic Discovery 真实评测

## 方法

每次评测都使用当前公开 Web Search，实际打开每条准备作为 Source Seed 的页面。完整 Candidate Set、网页笔记和原始链接保存在被 Git 忽略的 `discoveries/evaluations/`，公开仓库只保存去内容化汇总，避免把未经编辑判断的热点长期公开。

检查项：近期性、持续事件新进展、Source Seed 可打开性、匿名/纯传言排除、相同事件去重、类别上限、评分理由、首选与第 5 名排序、高风险弱证据降为 `watch`、无 Creator/engagement 数据时不造数，以及只回复编号形成 Research Handoff。

## V0.3 执行记录

执行日期：2026-08-10。评测入口分别为：

1. Broad：“今天有什么值得讲？”
2. Tech / Business：“最近科技商业有什么值得讲？”
3. Social / Public：“最近社会公共事件有什么值得讲？”

本次 Broad 与 Tech / Business 搜索各找到一个近期公开研究材料加一个独立背景/评测入口，均生成了一个可选候选；不是把一篇论文直接称作定论，而是以“证据边界”为研究问题。Social / Public 场景只找到快速公共安全活动线索、没有可核查事故或责任事实及两个独立来源，因此结果是一个 `watch`，没有推荐卡。评测特意保留该结果：Discovery 的职责是拦住资料基础不足的热点，而不是为了输出数量降低标准。

三轮均验证了 Candidate Set 的历史保存和 Markdown 短卡片；Broad 场景还实际执行了 `研究 1` 的编号选择，生成 Research Handoff。Handoff 仅传递研究问题、风险和入口，没有把 Seed 描述提升为已确认事实。Creator signal 在本轮没有作为必须数据；没有记录或编造播放量、搜索指数或其他 engagement 数字。

去内容化汇总见 `evaluations/v0.3.0-summary.json`。若后续改变时间窗口、评分、Preflight、去重或渲染规则，必须重新运行以上三类评测，不得用固定示例替代真实网页检查。
