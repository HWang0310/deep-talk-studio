# PR #48 五视频完整口播提取验收（2026-10-24）

本轮最高需求：[Nexus / Owner final 6384621479](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6384621479)。继续原 `agent/issue29-topic-first` / PR #48，未合并、未打 tag、未发布。此目录是候选实现证据，不代表 Nexus 独立审核通过。

首页现为自带1～5条B站链接/BV→明确本批授权→下载/FFmpeg/本地Whisper→独立完整转写→全文复制/下载。跟踪参数规范化、BV去重、逐条错误与重试；不自动热门搜索，不在输入或ASR后自动调用LLM。用户可选向已配置模型发送全部转写，指定字数、风格生成一篇未审核稿，也可直接交外部AI。旧聊天、历史重命名/软删除/恢复和正式Gate保留在 `/advanced`，原Key设置继续在 `/settings`。

## 真实性边界

**本轮五视频浏览器验收是明确的离线工具夹具，不是真实B站五视频下载或真实Whisper识别质量验收。** 使用真实flow、存储、HTTP、浏览器UI、剪贴板和下载事件；元数据、媒体、yt-dlp/ffmpeg/Whisper进程边界及模型返回是fixture。真实第三方媒体下载0、新增真实付费模型调用0。模型fixture只验证显式授权、完整来源输入、单篇和自定义字数参数传递，不声称示例模型输出实际达到1234字或证明创作质量。

## 完整保存和实际导出

隔离根目录 `/tmp/deeptalk-five-browser-v2`，会话 `WBX-834c7186069061ae`。

- 每份完整TXT及时间码JSON：`/tmp/deeptalk-five-browser-v2/workbench/sessions/WBX-834c7186069061ae/references/<BVID>/`。
- 五个BVID按顺序为 `BV1usn26NEdp`、`BV1fixture02`、`BV1fixture03`、`BV1fixture04`、`BV1fixture05`。
- 五份原文各 **250段、11,374字符、TXT 26,511字节**；末句分别为对应BVID的“第250句：最后一行完整保留。”，五个TXT指纹不同。
- 合并稿：同会话根目录 `合并参考稿.txt`，**60,294字符、133,139字节**，含来源标题/URL/BVID和按顺序拼接的五份完整TXT。
- 合并SHA-256：`312bcef79d5b2f92099c74e042780d4e026814c2b750ba4fde8677b9f8434980`。
- 实际浏览器下载副本在仓库 `output/playwright/five_transcripts/`：`source-1.txt`至`source-5.txt`、`合并参考稿.txt`、`第一份.txt`、`第一份.json`（本地试用文件不提交Git）。逐份TXT及合并TXT与服务器文件逐字节一致，JSON解析后与完整时间码源相等。
- 对五个“复制全文”及“复制全部五份”实际点击，读取浏览器真实剪贴板与对应完整字符串逐字比较，一致。未用摘要替代全文。
- 每个媒体后缀均为核验夹具计数 `-12357播放.mp4`；单测另验证跨新批次计数变更后缀为 `-99999播放`，旧文件逐字节不变。无法核验计数沿用原获取函数的“播放量未知”规则。

[逐份路径、指纹、工具次数及完整性机器证据](export-evidence.json)。生产保存规则为本仓库 `workbench/sessions/WBX-*/references/BV*/`（TXT和JSON）与同会话根目录 `合并参考稿.txt`；下载视频优先复用已配置下载目录，未配置则保存到同会话 `media/`，不必设置模型Key。

## 实际浏览器走查

Chromium headed，桌面1280×900及手机375×812；手机检查文档不横向溢出。

| 场景 | 证据 |
|---|---|
| 多行粘贴带tracker链接、五个BV及一个重复BV；未授权不执行 | [01](screenshots/01-consent-required.png) |
| 获取、FFmpeg、Whisper阶段按实际边界推进；无模型自动调用 | [02](screenshots/02-local-progress.png) |
| 第三条首轮403夹具，明确失败；其余四条继续并完整保存 | [03](screenshots/03-four-success-one-failed.png) |
| 实际点“重试此视频”，只重试第三条，5/5完整保存 | [04](screenshots/04-five-complete.png) |
| 实际展开全文（含250段，非前20段）和单份/合并下载 | [05](screenshots/05-full-transcript.png) |
| 自定义1234字、风格、单独费用授权，融合一篇未审核稿 | [06](screenshots/06-optional-one-custom-script.png) |
| 手机五份全文入口、复制和导出，无横向溢出 | [07](screenshots/07-mobile-five-transcripts.png) |
| 终止并重启隔离服务到相同根目录，刷新恢复五份及融合稿，复制仍逐字相等 | [08](screenshots/08-process-restart-recovery.png) |
| 真实本机8321首页已切到新默认工具（未下载视频/调用模型） | [09](screenshots/09-live-8321.png) |

工具边界日志：yt-dlp尝试6次（第三条先失败再重试）、FFmpeg5次、Whisper5次、模型fixture1次（仅显式融合）。刷新/进程重启不增加这些次数。五个来源标识分别进入各自250段，独立保存。初次证据核对发现夹具没有把FFmpeg临时WAV映射回来源，已修正夹具并在上述v2新根目录完整重走，所有本目录截图/机器证据均为修正后的运行。

## 测试与数据保护

- 最终完整 `PYTHONPATH=src .venv/bin/python -m pytest -q`：**1165 passed / 7 skipped，254.57s**。
- 最终裸入口 `PYTHONPATH=src python3 -m unittest discover -s tests -v`：**1172 tests，OK / skipped=7，255.354s**。
- 新增6个五稿回归用例：URL规范化/去重/非法输入；授权/五份完整导出/失败重试/幂等；独立批次、播放量变更、旧文件保留及新flow恢复；无Key本地ASR/默认media目录；路径与符号链接拒绝；真实HTTP路由及可选融合的完整来源、字数参数和未审核标签。
- 初轮17个旧首页静态断言失败，原因是它们仍要求根路径显示旧聊天/三稿。保留所有原断言，改为访问现保留能力的 `/advanced`；新首页由新增HTTP和实际浏览器用例验证。修正后定向89项通过，最终全量双入口通过。
- 新文件异常测试先复现：状态为complete但源文件丢失/符号链接会造成错误或越界写；现按实际文件失败关闭，阻止融合，符号链接重试不写外部目标。
- pytest和unittest均沿用临时用户设置/历史隔离。真实Owner用户设置与聊天9个文件哈希快照在测试、8321重启后逐字节一致。未输出Key或真实聊天。保留开工时5张旧截图的未提交更改及既有未跟踪目录。
- JS语法、`git diff --check`、保存Key精确值泄漏扫描通过。8321的 `/healthz`、`/`、`/settings`、`/advanced` 实测200。真实平台阻拦、缺本地Whisper仍如实失败，不下载模型、不绕过平台限制。

复现（只使用隔离fixture Key/数据）：

```sh
PYTHONPATH=src python3 evaluations/five_transcripts/serve_fixture.py --port 8325 --root /tmp/deeptalk-five-new-trial
# 浏览器粘贴上述五个BV，第三条首次失败，点其重试；可选显式融合。
python3 evaluations/five_transcripts/verify_exports.py --root /tmp/deeptalk-five-browser-v2 --downloads output/playwright/five_transcripts --output /tmp/five-export-evidence.json
```

融合完整输入上限100000字符，超限如实提示交给支持长文的外部AI；保存、复制和导出的原文没有截断。ASR准确率和真实模型创作质量仍由真实材料使用评估，fixture不替代这类验收。

READY_FOR_NEXUS_FIVE_TRANSCRIPTS_REVIEW
