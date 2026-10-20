---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '0561c1f4-ecdc-4c19-9dcb-ce07329a531a'
  PropagateID: '0561c1f4-ecdc-4c19-9dcb-ce07329a531a'
  ReservedCode1: 'ee0e60ab-8184-43cb-a0d8-4b91d63de1da'
  ReservedCode2: 'ee0e60ab-8184-43cb-a0d8-4b91d63de1da'
---

# Issue #26 Phase 1B — Mac 本地 Web UI 真实浏览器冒烟证据

日期：2026-10-20。环境：macOS，Chrome（Playwright 驱动），服务 `./scripts/deeptalk ui --port 8321`（真实匿名访客模式，绑定 127.0.0.1）。截图仅包含公开 B 站元数据与本地 UI，无私人内容。

| 截图 | 场景 | 验证点 |
|---|---|---|
| `01-empty-state.png` | 空态首屏 | 中文创建者界面、主题输入、0–5 链接添加、真实可用控件（无假 Settings/Script） |
| `02-real-search-results.png` | 真实检索（主题“莫斯科大学留学生旭日旗事件” + 用户链接 BV1waJi6dEXe 带 spm 参数） | 用户链接置顶标“用户链接”、“用户提供 + 搜索命中合并”溯源；自动候选 4 条按已核验播放量降序（478,313→258,659→104,932→100,828）；每条含标题/canonical URL（无 spm 参数）/UP/发布时间/抓取时间/播放量已核验状态；覆盖声明与查询词展示 |
| `03-empty-topic-validation.png` | 空主题校验 | 类型化中文错误“请先输入视频主题。”，不发请求 |
| `04-second-topic-with-rejection.png` | 换主题重跑 + b23.tv 短链 | 主题“俄罗斯乌克兰伊尔76运输机坠毁”发起新有界 run（20 条结果/12 次核验/新时间戳）；短链被拒并给出中文指引“暂不支持 b23.tv 短链，请粘贴完整链接”（脱敏 echo，无 token）；用户链接 BV1waJi6dEXe 仍置顶保留 |
| `05-narrow-screen-390px.png` | 390px 窄屏 | 响应式布局正常（iPhone 宽度） |

复现命令（Owner 验收用）：

```bash
cd deep-talk-studio
./scripts/deeptalk ui                 # 默认 http://127.0.0.1:8321/
# 或显式：./scripts/deeptalk ui --port 8321 --output discoveries
# 关闭匿名访客初始化：./scripts/deeptalk ui --no-visitor-identity
```

- 服务端工件落盘：`--output` 目录（默认 gitignored `discoveries/`），每次检索生成唯一 `reference-candidate-set-REF-*.json`，不覆盖。
- 离线确定性测试：`PYTHONPATH=src:. python3 -m unittest tests.test_webui`（26 项，注入 FakeProvider，不触网）。
- 已知限制：字面相关性启发式对刻意规避措辞依赖词元重叠（与 #24 相同）；本 UI 不含模型 API 设置（BYO 模型设置为独立后续 Issue）。
