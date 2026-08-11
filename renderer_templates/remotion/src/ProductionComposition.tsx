import "./index.css";
import {
  AbsoluteFill, CanvasImage, Easing, interpolate, Sequence, staticFile,
  useCurrentFrame, useVideoConfig,
} from "remotion";
import assetMapData from "./asset-map.json";
import profileData from "./production-profile.json";

export type DisplayText = {text: string; text_kind: string; claim_ids: string[]; evidence_link_ids: string[]};
export type Scene = {
  scene_id: string; scene_type: string; duration_frames: number; duration_seconds: number;
  source_material_ids: string[]; source_visual_ids: string[]; on_screen_text: DisplayText[];
};
export type ProductionPlan = {canvas: {width: number; height: number; fps: number}; scenes: Scene[]};

const assetMap = assetMapData as Record<string, string>;
const tokens = profileData.design_tokens;

const SceneBody: React.FC<{scene: Scene; still?: boolean}> = ({scene, still = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = still ? 1 : interpolate(frame, [0.15 * fps, 0.75 * fps], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const assetId = scene.source_visual_ids[0] ?? scene.source_material_ids[0];
  const asset = assetId ? assetMap[assetId] : undefined;
  const isCompleteGeneratedVisual = scene.source_visual_ids.length > 0;
  const revealRight = still ? 0 : interpolate(
    frame, [0.25 * fps, 1.2 * fps], [100, 0],
    {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.22, 1, 0.36, 1)},
  );
  return <AbsoluteFill style={{backgroundColor: tokens.colors.background, color: tokens.colors.foreground}}>
    <div style={{position: "absolute", inset: 48, border: `2px solid ${tokens.colors.surface}`, opacity: 0.7}} />
    {asset ? <CanvasImage
      src={staticFile(asset)}
      style={{position: "absolute", width: "100%", height: "100%", objectFit: "contain", clipPath: `inset(0 ${revealRight}% 0 0)`, opacity: entrance}}
    /> : <div style={{position: "absolute", inset: "100px 96px", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: tokens.colors.surface, opacity: entrance}}>
      <span style={{fontFamily: tokens.typography.display, fontSize: 86, fontWeight: 900}}>真人口播</span>
    </div>}
    {!isCompleteGeneratedVisual && <div style={{position: "absolute", left: 96, right: 96, bottom: 100, display: "flex", flexDirection: "column", gap: 12}}>
      {scene.on_screen_text.slice(0, 4).map((entry, index) => {
        const itemOpacity = still ? 1 : interpolate(frame, [(0.45 + index * 0.22) * fps, (0.9 + index * 0.22) * fps], [0, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1),
        });
        const translateY = still ? 0 : interpolate(frame, [0.3 * fps, 1.1 * fps], [32, 0], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp",
        });
        return <div key={`${scene.scene_id}-${index}`} style={{
          alignSelf: "flex-start", maxWidth: 1500, padding: "10px 22px",
          backgroundColor: index === 0 ? tokens.colors.accent : tokens.colors.surface,
          color: index === 0 ? tokens.colors.background : tokens.colors.foreground,
          fontFamily: index === 0 ? tokens.typography.display : tokens.typography.body,
          fontSize: index === 0 ? 58 : 34, fontWeight: index === 0 ? 900 : 400,
          opacity: itemOpacity, transform: `translateY(${translateY}px)`,
        }}>{entry.text}</div>;
      })}
    </div>}
    {!isCompleteGeneratedVisual && <div style={{position: "absolute", left: 96, top: 70, fontFamily: tokens.typography.data, fontSize: 22, color: tokens.colors.muted}}>
      ROUGH VISUAL · {scene.scene_type}
    </div>}
  </AbsoluteFill>;
};

export const ProductionScene: React.FC<{scene: Scene}> = ({scene}) => <SceneBody scene={scene} />;

export const RoughPreview: React.FC<{plan: ProductionPlan}> = ({plan}) => {
  let cursor = 0;
  return <AbsoluteFill>{plan.scenes.map((scene) => {
    const from = cursor;
    cursor += scene.duration_frames;
    return <Sequence key={scene.scene_id} from={from} durationInFrames={scene.duration_frames} name={scene.scene_id}>
      <SceneBody scene={scene} />
    </Sequence>;
  })}</AbsoluteFill>;
};

export const HeroStill: React.FC<{scene: Scene}> = ({scene}) => <SceneBody scene={scene} still />;
