# PR #48 Owner 创作流程 UX 收口

依据 [Nexus issuecomment-6383823863](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6383823863)，继续原 PR #48，起点 `ee04ea7ec9ce04f13a03c291fd009063bdeb925e`。单一执行工程师；未开新 PR、未合并/打 tag/发布。最终 exact head 与本机8321运行SHA见本轮 `READY_FOR_NEXUS_OWNER_FLOW_REREVIEW` 评论。

## 普通用户现在怎么走

1. 输入“我想做一期王扁被打的视频”，或在空聊天输入短选题“王扁被打”。页面只给本地短提示和四步进度，不调用模型写长稿。普通问候、问句继续走普通聊天。
2. 聊天里直接显示醒目的 **选参考并开始分析**，不再先找折叠项或弹窗。展开后默认选本轮最高播放量参考，可以改选。
3. 勾选一句 **我有权下载这些视频，并授权仅在本地学习分析**，点确认。实际运行阶段依次显示下载/读取已有文件 → 抽音 → Whisper转写 → 爆点分析 → 生成三稿，含已用秒数和失败信息。不会悄悄自动重试收费。
4. 分析与完整ASR就绪后，三篇口播直接出现在聊天并保存为稿件版本。用户可以继续发“吐槽版更损点”，新回复可直接复制、导出；查看/编辑保存稿件是可选动作，编辑器生成后和刷新后都收起。
5. 不想处理参考时，直接点 **跳过参考，直接自由创作**；正文由代码标明“仅按选题自由创作 · 未分析参考视频”。不会把标题检索包装成已经看过视频。

旧正式工作流只在 **设置 → 高级设置 → 打开旧版正式工作流** 中显式进入，刷新又默认隐藏。数据、Key、历史菜单、全ASR、视频命名与正式Gate均保留。输入框改为跟随文档流，编辑器随内容长高；正文/稿件不再与固定输入层互相遮挡。

## 后端保证与回归

- 初次视频任务和未完成参考处理时的催稿均为本地流程提示，零写稿模型调用。只有明确跳过，或实际完整ASR+所选study分析完成，才允许写稿。
- 参考依据、当前选题、所选BVID、完整转写文件及分析状态由代码复核。只出现“分析成功”字段但没有真实转写文件，不足以写视频二创。一个批次部分成功，也不会借第一条成功状态冒充整批完成。
- 选题选择、待分析批次和自由创作方式持久化；旧记录兼容，保留原始聊天文本与不可变稿件版本。切到自由创作时不注入上一轮参考分析摘要；ASR消失时不能继续冒称基于视频。
- 编排端点 `/api/workbench/chat/create` 是同源loopback、带body上限的SSE；同会话的流/草稿/重命名删除冲突仍409。在飞预约直到worker结束才释放；断线在后续阶段停止，已经产生的费用不承诺退回。
- 授权只有明确勾选才成立，限定当前聊天/发现turn/候选ID；仅记录用户声明，不伪造成许可证或正式Rights批准。保留平台风控失败和缺Whisper不自动安装行为。
- 分析失败也保留完成的完整ASR供查看/导出，retry复用已下载文件，不重新生成重复媒体。所有正式研究、事实核查、版权、审核及生产Gate未放宽。
- 原topic-first测试中“标题后立刻调用模型”的旧断言按Owner新流程调整为零调用；来源隔离、注入、幂等、SSE、历史和正式Gate回归保留，通过明确自由创作动作继续检验相关上下文。

## 浏览器实际走查

Chromium、隔离用户目录，桌面1280×800、短屏1280×500、手机375×812。全部通过实际UI点击、输入、下载；另用几何断言证明保存按钮在composer上方、编辑器无内部纵向溢出、手机文档无横向溢出。编辑中键入字符没有程序性跳屏。

| 场景 | 截图与实测 |
|---|---|
| 只输入选题，短提示/四步/主CTA，没有抢先三稿 | [01](screenshots/01-topic-next-action.png) |
| 选最高播放参考，改选与勾选式授权，未勾选无法开始 | [02](screenshots/02-inline-selection-consent.png) |
| 实际阶段回调、已完成阶段与Whisper处理中 | [03](screenshots/03-real-phase-progress.png) |
| 三篇完整稿在聊天里，编辑器未自动弹开 | [04](screenshots/04-three-scripts-in-chat.png) |
| 增加80行长稿，短屏末尾和保存/复制/导出在输入框上方 | [05](screenshots/05-short-height-editor-tail.png) |
| 手机同样可滚动到全部控件，稳定状态无侧栏遮挡 | [06](screenshots/06-mobile-editor-controls.png) |
| 纯标题“王扁被打”→明确跳过→仅按选题稿，继续改稿并导出回复 | [07](screenshots/07-mobile-bare-topic-free.png) |
| 无参考结果仍明确提供自由创作下一步 | [08](screenshots/08-no-reference-next-step.png) |
| Whisper刻意失败，没有视频稿；可重试、再失败、明确跳过 | [09](screenshots/09-failure-retry-skip.png) |
| 设置里的高级入口，日常聊天不再见旧阶段 | [10](screenshots/10-settings-advanced-entry.png) |
| 从新流程入口打开完整250段ASR、滚动阅读和实际TXT下载 | [11](screenshots/11-full-asr-retained.png) |
| 刻意慢检索超时后可自由创作 | [12](screenshots/12-timeout-free-path.png) |
| 旧流程只有显式进入才出现，刷新默认再隐藏 | [13](screenshots/13-advanced-workflow-opt-in.png) |

额外验证：实际保存到v6，刷新编辑器收起，重新打开v1与原文逐字一致，v1 Markdown下载成功。改稿回复的Markdown、ASR TXT也实际下载到gitignored `output/playwright/owner_flow/`。没有把Owner真实会话拿来做删除或改稿试验。

截图复查纠正了主CTA被通用白按钮样式盖成白字白底的问题；浏览器先复现同色，再验证可见主色按钮。高级入口也先复现hidden残留导致打不开，再修复并重走。手机截图等待侧栏过渡完成后重拍，避免用动画过渡帧证明最终布局。

## 真实性与费用

本轮是UX回归，**新增真实付费模型调用0，第三方视频下载0**。来源标题、计数、媒体、外部工具与模型均使用明确标识的离线合成夹具。运行真实flow/store/HTTP/SSE/UI，但不冒称本轮做了真实平台媒体下载或新的真实ASR/模型质量验收。前轮真实公开检索、DeepSeek与本地原创合成视频ASR证据仍在 [remix_one_shot](../remix_one_shot/README.md)。

夹具逐视频播放量987654/123456，检索摘要故意给99999999，实际下载文件名仍使用987654播放后缀。失败重试后该隔离根目录共2个媒体（成功任务1个、失败任务1个），没有为重试重复下载；成功参考全文有250段及独立TXT。临时根目录为 `.../deeptalk-remix-trial-p3fxzj53/`，媒体、转写及聊天未提交Git。

## 测试与隐私

- `PYTHONPATH=src .venv/bin/python -m pytest -q`：**1159 passed / 7 skipped，245.61s**。
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：**1166 tests，OK / skipped=7，246.081s**；裸入口保持用户级Key/聊天目录隔离。
- focused `tests/test_owner_flow.py tests/test_remix.py tests/test_workbench.py tests/test_webui.py`：179 passed（包括6个新Owner-flow用例及原回归）；并通过上述最终全量复跑。
- 新用例覆盖零付费预览、纯标题元数据/问候、明确跳过、授权与缺转写阻断、部分成功不能全量冒称、失败仍留ASR、完整阶段链、自由创作不带旧分析、ASR消失后禁止冒称、HTTP SSE/409/授权。
- 开工私有摘要快照为6个Owner用户文件；到收尾前逐字节一致。最终8321重启、Key掩码、历史/草稿数与SHA在readiness评论只报告元数据，不输出Key或真实聊天内容。
- 保留开工时5张无关旧截图的未提交更改与既有未跟踪目录；仅提交本轮明确文件。JS语法与diff检查、保存Key精确值泄漏扫描均在交付前执行。

复现夹具（不使用真实Key，不读取Owner会话）：

```sh
PYTHONPATH=src .venv/bin/python evaluations/remix_one_shot/serve_fixture.py --port 8323 --phase-delay 1
```

新建聊天分别输入“我想做一期王扁被打的视频”“王扁被打”“我想做一期无参考测试的视频”“我想做一期转写失败测试的视频”“我想做一期超时测试的视频”即可复现。fixture检索超时上限4秒以便回归，生产仍为12秒；外部阶段故意延迟1秒以观察真实回调顺序。流程有原型作者自查，最终Owner体验与Nexus独立exact-head复审仍待完成。
