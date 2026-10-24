# PR #48 Unified Save Folder Acceptance

Real headed Chromium browser, driven through Playwright CLI against a loopback-only fixture server. The fixture uses synthetic local video bytes, deterministic metadata, fake FFmpeg/Whisper runners, and temporary user settings/chat/session directories. No Bilibili, DeepSeek, paid model endpoint, owner API Key, or owner history was accessed.

## Browser path

1. Entered a temporary existing save root in `/settings` and saved once; the persisted setting was read back in the same temporary user configuration.
2. Started a three-video task. Videos 1–2 were present under the task's `视频/` and `口播稿/` folders with the merged reference file while item 3 failed with a simulated `ProxyError` for `127.0.0.1:7897`. The page displayed actionable proxy guidance and offered a single-item retry.
3. Retried only item 3. It completed, all three originals retained the `12345播放` suffix, all TXT/JSON exports and the merged reference were present, and reloading restored the completed task and its actual path.
4. Selected a prior session-local task and used “复制归档到保存文件夹”. SHA-256 checks confirmed the archived media/TXT/JSON matched their historical sources, and all source files remained present. Clicked “打开文件夹”; the browser fixture recorded the selected session path rather than launching Finder.
5. Checked at 375px viewport: `document.documentElement.scrollWidth` was 360px, with the path wrapping and controls remaining usable.

## Evidence

- `screenshots/desktop-all-three-saved.png` — completed three-item task, exact saved paths, TXT/JSON, original media, and play-count suffix.
- `screenshots/mobile-375px-save-path.png` — narrow layout with selected batch path and open-folder action.

## File layout example

```text
<保存根目录>/<时间>_PR48-统一保存验收/
├── 视频/离线测试 BV1web000001-BV1web000001-12345播放.mp4
├── 口播稿/01-离线测试 BV1web000001-BV1web000001.txt
├── 口播稿/01-离线测试 BV1web000001-BV1web000001.json
└── 合并参考稿.txt
```

The browser fixture also copied one historical local-session video and its TXT/JSON into a separate `归档-<日期>` batch, without moving the originals.

## Test results

- `PYTHONPATH=src python3 -m unittest tests.test_workbench tests.test_five_transcripts -v` — 95 tests, OK.
- `PYTHONPATH=src uv tool run --with pytest pytest -q` — **1179 passed, 7 skipped, 186 subtests passed**, 240.36s.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` — **1186 tests, OK (skipped=7)**, 240.479s.
- `git diff --check` and added-content credential pattern scan — clean.

The first full run exposed the renamed “下载位置” static assertion and missing ignored Remotion dependencies in the isolated worktree. The assertion now checks the requested single “保存文件夹” control. Verification then used the original checkout's existing `node_modules` through a temporary local symlink; the final full runs above passed. No dependency install or application configuration change was needed.

A read-only review identified existing manual TXT regeneration, late-root legacy retry placement, and a symlinked per-video archive boundary. Three new tests first reproduced these failures. The fixes preserve hand-edited TXT and local merged files, allocate a batch for delayed-root processing, and reject the symlinked per-video directory before reading download records. These cases are included in the final full results.

Browser verification was repeated after these fixes. The path field fallback was used in the real browser; the native macOS picker/cancel flow is covered by isolated `osascript` boundary tests. Folder-open routing was exercised with the fixture recording the destination, while the platform command implementation remains separate. The only console resource error was the existing missing `/favicon.ico`.
