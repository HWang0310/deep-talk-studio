# Issue #30 真实 CLI E2E 证据（2026-10-21，Nexus CHANGES_REQUIRED 修复后刷新）
合成中文语音（macOS say，非私人音频）→ 真实 whisper.cpp large-v3 → `./scripts/deeptalk align-video --session` → 剪辑表。
上游素材为自建合成 fixture：M001.png 附可核验公共领域权利页（唯一可入包素材）；M002.mp4 等未找到可核验复用依据，按权利 Gate 转为 AUDIO_ONLY 人工补画面行，不进 asset manifest。运行含正式 Clean A-roll Gate 与 audio_delivery 正式 QA。
