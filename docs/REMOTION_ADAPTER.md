# Remotion Adapter 0.6

- 锁定 `remotion/@remotion/cli 4.0.507`、React 19.2.3。
- 使用 `useCurrentFrame`、`useVideoConfig`、`interpolate`、`Sequence`、`staticFile` 和 `CanvasImage`；不使用 CSS animation/transition。
- 为每个 Scene 建立 Composition，另建 RoughPreview 和 HeroStill。
- Studio 使用 `--no-open`；渲染优先复用已安装 Chrome，显式绑定 project `public/` 并使用单并发保证本机可重复性。
- 正式顺序：`npm ci → lint/tsc → compositions → Studio preview → render/still → ffprobe/QA`。
