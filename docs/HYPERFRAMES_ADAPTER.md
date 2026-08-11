# HyperFrames Adapter 0.6.1

- 锁定 HyperFrames 0.7.106 和 GSAP 3.14.2；每次先生成 `DESIGN.md`，再生成 HTML。
- 四类 `scene_payload` 生成独立 DOM/SVG 元素和独立 GSAP 定义；布局先于动画，timeline 均 `paused: true` 且同步注册到 `window.__timelines`。
- 禁止 random、系统时间、async timeline 和 `repeat: -1`。diagram edge 的动画时间必定晚于两个 endpoint node。
- rough preview 使用新 scene 覆盖式入场，不在旧 scene 上预先执行 opacity exit。
- raw PDF 与四类 V0.5 SVG 不进入 `<img>`；只有批准 image capture 可使用轻推、平移和高亮。
- typed QA 顺序：`npm ci → doctor → lint → validate → inspect → preview/status/stop → render → ffprobe`。
