# HyperFrames Adapter 0.6

- 锁定 HyperFrames 0.7.106 和 GSAP 3.14.2。
- 每次先生成 `DESIGN.md`，再生成 HTML Composition。
- 布局先于动画；GSAP timeline 使用 `paused: true` 并同步注册到 `window.__timelines`。
- 使用 `.clip`、`data-start`、`data-duration`、`data-track-index`；不使用 infinite repeat、`Math.random()` 或异步 timeline 构建。
- 素材路径从 project root 解析，可通过官方 `HYPERFRAMES_BROWSER_PATH` 复用本机 Chrome。
- 正式顺序：`npm ci → doctor → lint → validate → inspect → background preview/status/stop → render → ffprobe/QA`。
