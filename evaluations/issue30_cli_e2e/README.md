# Issue #30 真实 CLI E2E 证据（2026-10-21，Nexus 第二轮 CHANGES_REQUIRED 修复后刷新）
合成中文语音（macOS say，非私人音频）→ 真实 whisper.cpp large-v3 → `./scripts/deeptalk align-video --session` → 剪辑表。
上游素材为自建合成 fixture：M001.png 的权利数据是模拟核验数据（example.com 占位，未发生真实联网核验，非真实第三方复用许可，仅用于验证 Rights Gate 按合同放行/拦截），经 Gate 放行后照表入包；M002.mp4 等未找到可核验复用依据，按权利 Gate 转为 AUDIO_ONLY 人工补画面行，不进 asset manifest。剪辑表前言为纯音频语义：不暗示任何真人画面；有素材段照表使用，缺口段需人工补画面。运行含正式 Clean A-roll Gate 与 audio_delivery 正式 QA。
