# DeepTalk Studio 路线图

路线图描述方向，不代表所有功能必须一次完成。每一阶段都应先用真实内容验证价值，再扩展自动化。

## V0.1：项目基础与 Research Workflow（已完成）

- 正式仓库、长期协作文档和版本记录；
- 仓库级 `research-topic` Skill；
- 来源、主张、观点、冲突、角度和 Script Agent 交接契约；
- Markdown/JSON 双格式报告；
- 校验器、命令行、离线示例和自动测试；
- 可替换的 OpenAI 联网研究提供器。

## V0.2：研究质量与事实核查（已完成）

- Research Report 0.2、Evidence Ledger 和完整 Schema 校验；
- 独立 FactCheck Artifact、第二次搜索和反证记录；
- 来源 provenance、去重、转载识别和独立性分组；
- 高风险主张队列和透明质量 Gate；
- 不可覆盖的报告修订、补充来源和更正历史；
- 三类真实题材评测和人工 Review 表。

### V0.2.1：Quality Gate Hardening（已完成）

- 修正 unknown / related / duplicate / syndicated 来源的独立确认计数；
- API Research 改为只接收研究内容，机器字段由程序确定；
- Fact Check 新来源与原来源统一规范化和独立性归组；
- 收紧 context-only、未匹配 attribution、重复转载对质量指标的影响；
- 保持 Research Report 0.2 契约和原质量阈值不变。

## V0.3：Topic Discovery（已完成）

- 支持“我不知道今天讲什么”的入口；
- 聚合近期社会、商业、科技、网络和公共事件；
- 结合新鲜度、讨论度、观点冲突、可核查性和频道匹配度评分；
- 输出候选选题卡，由用户简单确认后进入 Research Workflow；
- 参考创作者关注方向，但不抓取或模仿其稿件。
- 保持人工选题确认，确认后才进入 V0.2 Research Workflow。
- 新增 Channel Profile、Topic Candidate Set 0.3、Source Seed Preflight、透明五维评分、资格 Gate、事件去重、类别多样性和不可覆盖的 discovery 历史；
- 新增 `discover-topics` Skill，支持用户回复编号后直接交给 `research-topic`，不重复要求标题；
- 三类真实 Discovery 评测和去内容化汇总。

## V0.4：原创 Script Agent

- 只读取通过 Review 的 Research Report；
- 生成原创分析框架、故事线和口播稿；
- 保留事实标签、归因和禁讲项；
- 支持口语节奏、信息密度、时长和版本对比；
- 增加稿件事实回链和相似表达风险检查。

## V0.5：素材与视觉辅助

- Material Search：推荐公开文件、截图、图片、视频片段和图表；
- 标注来源、版权风险、建议使用位置和时长；
- Visual Generation：生成原创图表、时间线、地图和说明动画；
- 评估接入 Remotion、HyperFrames 或其他视觉工具。

## V0.6：剪辑与发布辅助

- 生成镜头级剪辑方案和素材清单；
- 辅助字幕、章节、标题、封面文案和发布说明；
- B 站发布前检查；
- 在运营数据足够后扩展小红书、抖音等平台适配。

## 暂不承诺

- 全自动无人审查发布；
- 自动采信网络传言；
- 大规模下载或保存受版权保护素材；
- 为追求“像某位创作者”而建立模仿模型。
