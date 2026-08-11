# V0.5 Material Search & Visual Assistance 真实评测（V0.5.1 复跑）

评测日期：2026-08-11。完整真实 Script、Research、Material Package、Review Artifact 和本地 SVG 保存在 Git 忽略目录；公开仓库只提交去内容化汇总 [`evaluations/v0.5.1-summary.json`](../evaluations/v0.5.1-summary.json)。

## 方法

使用 V0.4 已批准的稳定商业和争议公共议题 Research/Script，重新建立 V0.4.1 Review linkage 后进入正式 V0.5 Gate。实际打开并记录 Apple 官方财报页、EUR-Lex/欧委会页面、欧委会 CC BY 4.0 reuse notice、普通新闻页；没有调用用户 API Key。素材数据、权利和 URL 由真实页面检查，包的 ID、资格、排序、SVG 和 Review Gate 由正式代码生成。

V0.5.1 再次检查 A Stable Business、B Contested Public、C Rights / Sparse：权利页必须有独立 actual-open record，不能由名称推断。另加入 D（素材页已打开、CC 权利页未打开）、E（comparison 内部 C404/E404）和 F（手改 reviewed r2 的 rejected item）三个 fail-closed 场景。

另有一个隔离的下载安全场景，用明确复用的虚构 press asset 验证实际 PDF 保存、大小、路径和 SHA-256；它只验证工程获取链路，不伪装成真实新闻资产。

## 三类结果

| 场景 | 关键验证 | 结果 |
|---|---|---|
| A Stable Business | 官方财报页实际打开；页面 `all rights reserved`，因此保守为 reference-only；核心数字由 approved Claim 生成实际 bar SVG | `reviewed`；1 reference-only；1 原创 SVG 本地文件 |
| B Contested Public | 欧委会页面与 CC BY 4.0 reuse notice 实际打开；普通新闻页实际打开但无明确复用许可 | `reviewed`；EU 页面 ready-to-use；新闻页 reference-only；1 timeline SVG |
| C Rights / Sparse | AP 新闻页实际打开，未从媒体名称推断版权；不下载新闻画面，改用 Research-grounded diagram | `reviewed`；0 现成 ready item；1 reference-only；1 原创 SVG |

B 证明“网页能打开”不等于“新闻图片可直接使用”。C 证明素材稀缺时，系统宁可给 reference-only 链接和原创画面，也不把未知版权伪装成许可。

## 实际资产检查

- 三类场景均生成可打开的 1920×1080 SVG，包含 attribution metadata 和 Claim/Evidence metadata。
- A 的 1094、16、2.02 均来自批准 Claim；若改成 999，validator 在 render 前拒绝。
- B 的两个日期和 Claim 组合均来自 Research timeline。
- C 的关系图明确表达“披露来源不等于内容准确”，不伪造真实场景。
- 隔离下载场景实际写入 PDF，记录 MIME、字节数和 SHA-256；重复下载拒绝覆盖。

## 人工编辑检查（1–5 分）

| 维度 | A | B | C | 说明 |
|---|---:|---:|---:|---|
| provenance_truthfulness | 5 | 5 | 5 | 搜索摘要和 actual open 分离 |
| claim_evidence_alignment | 5 | 5 | 5 | 证据画面均绑定已批准 Research |
| rights_conservatism | 5 | 5 | 5 | Apple/新闻未知权利没有变 ready |
| visual_readability | 5 | 5 | 5 | 16:9、高对比、标题与署名可读 |
| editorial_usefulness | 4 | 5 | 4 | A/C 受权利稀缺限制，但有可用替代 |
| non_misleading_use | 5 | 5 | 5 | 原创图不冒充新闻或现场证据 |
| **平均** | **4.8** | **5.0** | **4.8** | 三类均通过独立 Material Review |

## 已知限制

- Rights Gate 只能证明检查时记录的公开依据，不能代替律师意见或后续许可变化监控。
- 网页截图仍需编辑确认裁切是否完整；工程记录不能自动判断所有视觉语境误导。
- V0.5 给出建议秒数，不进行音频对齐，也不生成完整视频。
- API Web Search 结果只升级为 `discovered`；若没有 actual-open manifest，仍不能成为 inspected/ready-to-use。
- r2 的最终资格和状态由 r1 provenance + Review Artifact 重建；普通 package digest 不是可信证明。
