# PR #48 — 爆款二创 1.0 一次性交付证据

2026-10-24（Asia/Shanghai）。按 Nexus 最终评论 [6383273699](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6383273699)，结合 [6383140012](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6383140012) 与 [6383162084](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6383162084) 执行。唯一执行工程师 Codex；原分支 `agent/issue29-topic-first`，原 PR #48。原始 head `ae8e0f2b0fab6872265c4787fc4577524b565bf2`。未合并、未打 tag、未发布；最终 exact PR head 与本机8321启动 SHA 见本轮 GitHub readiness 评论。

## 结果与体验

- 输入明确热点后，发送即显示准备检索；本轮相关参考按**逐视频接口核验**播放量降序排列。最多5条，未知不补数字，不是全站榜单。
- “参考灵感”按需展开，在参考工作区勾选视频、填写授权声明后下载/抽音/本地Whisper/分析；成功后自动生成一份含**犀利吐槽、搞笑玩梗、故事反转三篇完整口播**的未审核版本。三稿共用现有编辑器、复制、Markdown导出与历史版本；聊天可继续调“更损点/更有梗/节奏快些”，注入当前已保存稿件，换题则剔除旧稿。
- 完整ASR有独立弹窗、全文搜索、复制、TXT导出、含全部时间段的JSON导出。元数据与完整 `transcript.json` 保留，原子幂等写旁边的UTF-8 TXT；不是作者原始书面稿。正式工作流内的20段是预览，旁边提供完整全文入口，绝非最终转写上限。
- 历史 `···` 支持键盘与手机操作，重命名刷新后仍在；删除前确认标题/草稿数；移入本地回收站可恢复，无自动清除，不删除媒体或参考材料。生成回复/草稿期间冲突操作返回409。
- A→B同聊天来源、对话与草稿上下文隔离；legacy singleton可读，旧turn位置不变；B失败/超时不会套A来源。相同主题/turn重试幂等，超时迟到结果不回写，无付费自动重试。
- 原有正式 Research/Fact Check/Thesis/Reviewed Script/Rights/Production Gate未放宽。创作路径娱乐优先，不要求先过新闻采编表单。

## 三种真实性边界

| 证据 | 实际执行 | 未声称的能力 |
|---|---|---|
| [真实公开检索](real-public-search.json) | 免费匿名B站搜索+逐视频元数据，7.370秒；5条播放量依次1,159,172 / 142,940 / 82,777 / 50,964 / 591，均 `verified/per_video_api` | 不是全站榜单、权威事件核查或实际下载 |
| [真实DeepSeek三稿](real-model-three-drafts.md)、[更损版修改](real-model-revision.md) | 复用已保存Key，真实 `deepseek-flash`，恰4次新调用：初次聊天1、摘要1、三稿1、修改1。输入参考元数据/媒体/250段ASR明确为**合成夹具**；三稿是真实模型输出，未人工改写成“通过” | 不是基于真实B站视频ASR的已审核事件成稿；未查询货币费用，按服务商账单计费 |
| [真实本地ASR](real-local-asr.json) | 原创测试文本→已安装macOS Tingting合成语音→实际ffmpeg生成视频并抽音→实际whisper.cpp **1.9.2 / large-v3**→完整转写/TXT；1段0–18.56秒，82识别字符，媒体SHA留证；新增LLM调用0 | 没有下载B站媒体；BVID/URL只是夹具ID。叙事模型步骤刻意不再付费，状态 `unverified`，转写状态 `complete` |

真实模型三篇分别采用“标题空盒子与围观脑补”“节拍器/流水线”“三套情绪撞上测试文件”的叙事角度，均有正文、钩子、观点与收尾。随后“只把吐槽版改得更损”实际返回短句、排比和“自动脑补带宽/空投箱”等比喻。输入是合成材料，所以模型会提到验收样例；不能据此声称完成了真实人物事件质量验收。

## 下载与全文工件

浏览器端到端路径使用确定性 `yt-dlp/ffmpeg/Whisper/LLM` runner夹具，调用真实flow、store、HTTP和界面：

- 实际生成文件：`王扁被打 · 合成来源夹具 02-BV1fixture02-987654播放.mp4`。987654来自夹具逐视频元数据，搜索摘要故意给99999999，测试确认未采用摘要数。标题沿用sanitize_filename清理，并补UTF-8字节上限，避免连续emoji超出255字节文件名限制；未知命名、碰撞不覆盖、合并扩展名与外部路径拒绝另由自动化验证。
- 对应完整转写有250段，可搜索到“第250句”，复制到剪贴板包含尾句，TXT/JSON实际浏览器下载成功，JSON全部250段保留。文件在一次性根目录 `.../deeptalk-remix-trial-glqid1xa/workbench/sessions/WBX-ac5e6c045b6d4047/references/BV1fixture02/`；全文TXT名为 `王扁被打 · 合成来源夹具 02-BV1fixture02-口播转写.txt`。
- 真实本地ASR文本路径原样保存在 [real-local-asr.json](real-local-asr.json) 的 `txt_path`，源音视频为自行生成的测试数据。上述本地媒体/TXT留在临时验收目录，未提交Git。
- 老下载不重命名；同stem碰撞时在BVID前加随机片段，新文件仍以播放量标记结尾；`--no-overwrites`。重复成功分析复用study/transcript，显式重新分析入口才重跑模型。

## 浏览器回归（Chromium，桌面1280与375×812）

| 路径 | 结果 / 截图 |
|---|---|
| 热度排序、未授权拒绝、选择后授权处理 | [参考工作区](screenshots/01-ranked-references.png) |
| 自动三篇、完整版本编辑器 | [三稿](screenshots/02-three-drafts.png) |
| 第250句、复制全文、TXT/JSON下载 | [全文ASR](screenshots/03-full-transcript.png) |
| 重命名→刷新→取消删除→软删除→恢复 | [回收站](screenshots/04-trash-restore.png) |
| 同聊天A→B即时pending、刷新两条来源行原位保留 | [等待状态](screenshots/05-immediate-search-pending.png) |
| 刻意慢检索超时后继续回复 | [超时回退](screenshots/06-timeout-continues.png) |
| 375px聊天/菜单、键盘Enter、改名、取消删除、关闭再打开 | [手机聊天](screenshots/07-mobile-chat.png)、[键盘菜单](screenshots/08-mobile-keyboard-menu.png)、[reduced-motion](screenshots/09-mobile-reduced-motion.png) |
| 真实模型三稿、正常聊天修改 | [真实三稿](screenshots/10-real-deepseek-three-drafts.png)、[真实修改](screenshots/12-real-revision.png) |
| 静态装饰、无WebGL仍完整可用 | [空态](screenshots/11-static-polish.png) |

浏览器复查发现并修复手机侧栏关闭后遮罩残留/`collapsed`覆盖再次打开的旧问题。断言 `mobile close leaves backdrop active` 在修复前失败；修复后关闭/重开、键盘菜单、重命名、取消删除均通过。截图08等待抽屉进入视口后重拍，避免把过渡中的画面当成可用性证据。

Three.js **未启用**：选用合同允许的静态CSS方案；主体是聊天与文本，单独新增3D运行时没有明确体验收益。未声称做过Three.js性能A/B。实测当前375px页面DOM ready 9.5ms / load 10.1ms（回环、暖浏览器一次观察），5次Playwright输入往返为2/2/2/1/1ms；canvas=0，运行中animation=0，横向溢出=0。数字不是跨设备性能承诺。

## 自动化与隐私

- 最终全量命令：`PYTHONPATH=src .venv/bin/python -m pytest -q`；裸入口 `PYTHONPATH=src python3 -m unittest discover -s tests -v`。移动端与UTF-8文件名修复后完整复跑：pytest **1153 passed / 7 skipped，236.07s**；裸unittest **1160 tests / OK (skipped=7)，236.087s**。
- 14个新增确定性回归覆盖A→B成功/失败、legacy/reload、retry、timeout迟到、当前草稿修改、下载模板/碰撞/扩展名/路径、完整转写幂等、菜单存储/HTTP409/软删除恢复/symlink、缺Whisper不安装、真实JSON offsets、成功分析不重复付费。
- 历次focused：`tests/test_remix.py tests/test_workbench.py tests/test_webui.py` **172 passed**；最终UTF-8文件名修复后 `tests/test_remix.py tests/test_workbench.py` **89 passed**。两者均由最终全量复跑覆盖。无自动化读取OwnerKey/历史，测试沿用双入口临时用户目录隔离。
- 开工前私有文件摘要与收尾快照均只在本机 `/tmp`，不公开文件内容、Key或真实聊天。已核验Owner用户目录5文件字节摘要完全一致；8321最终重启与只读核验结果将在GitHub readiness评论报告。
- 保留开工时5张旧截图的未提交修改及所有无关未跟踪目录。本轮只按明确路径暂存；无真实聊天删除、分支重写、媒体上传、Cookie读取、付费搜索或新订阅。
- 依Owner“唯一执行工程师”要求未启用子代理；本轮为作者自查，**Nexus独立exact-head评审仍待完成**。

## 复现

```sh
PYTHONPATH=src .venv/bin/python evaluations/remix_one_shot/serve_fixture.py --port 8323
# 临时目录由服务启动时打印，所有媒体/模型为显式夹具。
# 真实模型模式需Owner已有授权和已保存设置，最多4次，绝不把Key复制进脚本/文件：
PYTHONPATH=src .venv/bin/python evaluations/remix_one_shot/serve_fixture.py --port 8324 --real-model
# 重启同一隔离试用可 --root <启动时打印的路径>；调用预算从记录恢复。
PYTHONPATH=src .venv/bin/python evaluations/remix_one_shot/run_local_asr_trial.py
# 只使用已安装运行时/模型；缺失时停止，不自动下载大模型。
```

本轮没有取得第三方视频下载许可，故不把合成媒体runner冒称实际B站下载成功。平台真实下载/长期会话质量仍受既有授权、平台访问与模型输出影响；不得绕过登录、风控或DRM。READY仅表示提交评审候选，不是Nexus已批准，也不是发布许可。

收尾自查补充：连续emoji标题原先生成270字节文件名，失败回归已复现；改为为标题保留最多160 UTF-8字节，媒体/TXT尾缀均保留，新增回归通过。移动端侧栏、普通聊天零检索提示与375px无溢出已再次实测。
