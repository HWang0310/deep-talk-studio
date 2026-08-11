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

### V0.3.1：Discovery Gate Hardening（已完成并验收）

- 新增 Codex 实际打开页面的后台 inspection manifest，未在其中的 Seed 必须保持 `unmatched`；
- Candidate Artifact 全部关键机器字段改为确定性重新推导和 fail-closed 校验；
- 收紧不同研究方向、时间一致性和 Raw Candidate 最小池规则；
- 类别多样性升级为先多样、再补位的软约束，并移除无效的 `--count` 参数；
- 重新执行三类真实 Discovery 评测，明确记录 `pass` / `fail` / `not_applicable`。

## V0.4：原创 Script Agent（已完成）

- 只读取完成 Fact Check、通过 Quality Gate、并有用户确认的新 Research Revision；
- 新增 Script Profile 0.4、Script Draft Artifact 0.4 和独立 Script Review Artifact 0.4；
- 生成原创分析框架、故事线、Editor Markdown 与纯口播 Teleprompter Markdown；
- 每个 Beat 明确区分事实、归因、分析、转场和问题，并保留 Claim / Evidence 回链；
- 硬阻止未批准 Research、直接使用禁讲结论、伪造机器字段和未核查高风险事实；
- 计算 must-keep coverage、口播字数与时长，支持自然语言调整时长和结构；
- Writer 与 Reviewer 分离，Reviewer 必须完成 15 个检查维度，阻断问题不能进入 `reviewed`；
- 稿件修订不可覆盖，并支持比较两个 revision；
- 完成稳定商业、争议公共议题和未批准输入三类真实评测。

## V0.4.1：Script Gate Hardening（已完成并验收）

- 将 15 项 Script Review checks 与受控 issue mapping 绑定；任一失败检查必须有对应 issue，八项事实安全检查必须对应 blocking issue；
- 仅 `counterargument_fairness` 可使用 `not_applicable`，事实安全检查不能借此绕过；
- `reviewed` Script 绑定可复验的 Review Artifact、来源 revision 与内容指纹；旧 Review 不随内容修订继承；
- Beat ID 采用稳定、递增、不可复用策略，版本比较能区分插入、删除、移动与实际修改；
- 完成 V0.4.1 受控 A/B/C 评测和 synthetic fail-closed 场景。

## V0.5：素材与视觉辅助（V0.5.1 已完成，待产品复核）

- reviewed Script + exact Research + V0.4.1 Review linkage 输入 Gate；
- Material Package 0.5、Cue Sheet、真实 inspection、Rights/Reuse Gate、Claim/Evidence binding；
- 安全静态文件获取、网页/PDF capture 登记、视频 reference-only 边界；
- Research update escalation，不用素材搜索静默改稿或制图；
- 原创 timeline/bar/comparison/diagram Visual Spec 和 1920×1080 SVG；
- 独立 Material Review、item 隔离、package Gate 和不可覆盖存储；
- `prepare-materials` Skill、API Provider、CLI 和三类真实评测；
- Remotion / HyperFrames 只保留 render target hints，未创建完整视频工程。

### V0.5.1：Material Gate Hardening（已完成，待产品复核）

- Rights actual-open provenance、rights evidence page 和工具引用一一绑定；
- Visual Spec 内部 timeline/bar/comparison/diagram grounding 全部 fail-closed；
- reviewed Material Package 通过 r1 provenance → Review → r2 的确定性重新证明；
- SVG sanitizer 与 PDF/截图校验加固；
- 仍未开始 Remotion / HyperFrames 制作层。

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
