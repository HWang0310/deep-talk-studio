# Remotion Adapter 0.6.1

- 锁定 `remotion/@remotion/cli 4.0.507`、React 19.2.3。
- 四类 Motion 直接消费 `scene_payload`：timeline baseline/marker、bar baseline grow/label/value、comparison independent sides/items、diagram node/edge。它们使用 React/SVG 原子元素，不使用 V0.5 整图 SVG 或 CanvasImage。
- 使用 `useCurrentFrame`、`useVideoConfig`、`interpolate`、`Easing` 和 `Sequence`；不使用 CSS animation/transition。CanvasImage 仅用于已通过 render boundary 的静态 image capture。
- 为每个 Scene 建立 Composition，另建 RoughPreview 和 HeroStill。
- typed QA 顺序：`npm ci → eslint → tsc --noEmit → compositions → Studio --no-open → render/still → ffprobe`。每项保存独立 exit outcome 和脱敏摘要。
- 渲染优先复用已安装 Chrome，显式绑定 project `public/` 并使用单并发保证本机可重复性。
