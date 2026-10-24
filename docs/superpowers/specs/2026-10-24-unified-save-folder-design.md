# Unified Save Folder — Design

## Intent

Let a creator choose one local save folder once and have each new five-video extraction batch automatically appear there as a self-contained archive. Preserve local session copies, existing media, full transcripts, the saved DeepSeek key, and unrelated chat history.

## Goals

- Reuse the existing user-level private downloads-folder setting as the single save root; keep it in `~/.deeptalk/workbench.local.json` with existing atomic writes and `0600` permissions.
- Offer a native macOS directory chooser with a validated absolute-path field as fallback, plus clear writable/existence feedback.
- Create a unique task folder containing `视频/`, `口播稿/`, and `合并参考稿.txt`. Download original media directly into `视频/`, retaining its verified play-count suffix.
- As each source finishes, save the complete transcript text and full JSON immediately and refresh the merged text. Retrying a failed source updates only that source and the merge.
- Display the actual batch path and offer an explicit folder-open action. Let the owner copy historical session artifacts into a new archive without moving or overwriting originals.
- Explain a refused configured local proxy accurately and offer checks for the running proxy and port without changing network settings.

## Non-goals

- No automatic proxy disabling, proxy bypass, or network-setting changes.
- No additional model calls, API-key changes, media re-download to archive, destructive migration, transcript truncation, merge, or release.
- No change to the advanced workflow's existing download behavior or to prior batch/session files.

## Constraints

- The existing workbench setting is stored at user scope and masked independently from the API key. Omitted settings fields must remain unchanged.
- Download consent remains required before Bilibili acquisition.
- Archive only validated local artifacts, reject symlinked per-video folders, use collision-safe task directories, and write files without clobbering unrelated existing paths.
- Existing session-local persistence remains the fallback when no save folder is configured.
- The owner requested implementation without another design round; implementation details below are engineering decisions made to complete that request.

## Approaches

1. **Reuse the existing downloads-folder setting as the one save root (selected).** This preserves the existing user-level setting store and its permissions. New extraction batches add a private subfolder beneath it; the current advanced workflow continues to use the configured path as before.
2. Add a second auto-save setting. This would create two user-visible local paths that users must keep in sync, against the one-folder requirement.
3. Store a browser directory handle. A browser handle cannot provide the backend with a trusted local path for yt-dlp, FFmpeg, or Whisper output.

The selected approach keeps one configured path and uses a macOS-native directory picker when available; path entry remains an accessible fallback.

## Behavior and data shape

- The existing setting `downloads_dir` is rendered as **保存文件夹** on `/settings` and validated as an existing writable absolute directory. A user may leave it blank to keep session-local output.
- A new batch receives a sanitized optional label, defaulting to a local timestamp and task name, plus a collision-safe suffix. Its path is persisted in the existing session record so refresh/restart continues to target the same folder even if the setting later changes.
- Each batch contains `视频/`, `口播稿/`, and `合并参考稿.txt`. Per-source names include ordinal, safe title, and BVID; JSON retains the full timed transcript and source metadata. The original media filename remains unchanged.
- New source files use exclusive creation. Repeated state reads recognize their recorded hashes; mismatched existing files are reported and preserved. The merged file is atomically replaced only when it still matches the prior generated hash.
- Existing hand-edited transcript TXT and session merge files remain byte-identical during state refresh and archive. Generated merge output updates only if it still matches its recorded prior hash. A legacy retry after a root is selected first receives a batch folder (copy-archive when legacy files exist), so downloads never go directly into the root.
- Historical archive is explicit and copy-only. It copies available verified media and canonical full TXT/JSON artifacts to a new task folder; absent media does not block transcript archiving. Repeating the operation reuses the session's recorded archive location.
- Folder opening resolves only the destination stored for that session. Proxy errors are classified separately from transcription errors and do not retry with proxy settings changed.

## Validation

- Focused settings, archive, retry, manual-edit preservation, symlink boundary, migration, proxy-error, and HTTP/UI tests use temporary user settings/session roots and offline media/Whisper fixtures.
- Run the full pytest and unittest suites under isolated user configuration.
- Use Playwright in a real Chromium browser at desktop and mobile widths to configure a temporary folder, process an offline batch with a failed third item, retry it, check exact saved bytes and paths, refresh, and copy-archive an older session. Do not make paid model calls or contact Bilibili.
- Keep browser captures in the existing project evaluation/output locations and distinguish offline fixtures from real ASR evidence.
