# V0.6 Production Evals

评测日期：2026-08-11。完整渲染工程、node_modules、真实 package 和输出被 Git 忽略；公开仓库只保留去内容化结果。

## A. Stable Business

使用已审 Apple 2026 财年第三季度 Research、稿件和 bar Material 重放当前 Gate。新版页码 Gate 拒绝了旧 `page_number=0`，评测新包改用 1-based 页码。含 `2026` 的标题作为 factual text 绑定 C1/E1/E2。Remotion 完成 project、validation、preview、render 和 QA，生成 bar MP4、rough MP4 和 PNG，package Gate = `pass`。新闻网页继续 reference-only。

## B. Contested Public

使用欧盟 AI Act 第 50 条 timeline 与官方页/新闻页。日期只有在 date/event/Claim/Evidence 与 approved Research Timeline 精确一致后通过。Production Plan 生成 `timeline_motion + A-roll placeholder`；TechRadar `reference_only` M002 未进入任何 Scene，未安全落地的官方页不被假装为本地截图。

## C. Rights Sparse

输入只含 AP 新闻 reference-only 和从 approved Research 生成的 diagram。Production Plan 只选 `diagram_motion + A-roll placeholder`，没有任何 source material ID 进入 renderer，也没有下载新闻素材。

## D. Blocked Input

`draft`、`blocked`、`research_update_required`、fake reviewed 和缺 canonical provenance 均由 `validate_production_input` 在 renderer factory 之前拒绝。

## E. Cross-renderer Compatibility

同一 `PROD-v060-cross-renderer` tiny Plan（同数据、文字、1.0 s Scene、source binding）分别运行两个 adapter。

| Renderer | MP4 | 尺寸 / fps | 时长 | QA |
|---|---:|---|---:|---|
| Remotion 4.0.507 | 2 | 1920×1080 / 30 | 1.045333 s | pass |
| HyperFrames 0.7.106 | 2 | 1920×1080 / 30 | 1.000000 s | pass |

两者各生成 1 张 1920×1080 PNG。输出字节不要求像素一致，但语义 Plan 与 source binding 一致。

## F. Asset Tampering

在已记录 asset 后改写本地文件，byte size/SHA 复核在 renderer 前 fail closed。路径越界、missing file、MIME 不匹配和 reference-only local injection 也被覆盖。

## Tests

- 常规 unittest：255 total，254 passed，1 skipped real-render test；原 219 项全部保留。
- 真实渲染：设置 `DEEPTALK_RUN_RENDER_INTEGRATION=1` 后，cross-renderer integration 1 passed。
- Skill Creator `quick_validate.py`：`produce-video-assets` passed。
