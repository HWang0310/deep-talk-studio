import "./index.css";
import {
  AbsoluteFill, CanvasImage, Easing, interpolate, Sequence, staticFile,
  useCurrentFrame, useVideoConfig,
} from "remotion";
import assetMapData from "./asset-map.json";
import profileData from "./production-profile.json";

export type DisplayText = {
  text: string; origin: string; text_kind: string; claim_ids: string[]; evidence_link_ids: string[];
};
type TimelineEvent = {order: number; date: DisplayText; label: DisplayText};
type BarPoint = {order: number; label: DisplayText; value: number; value_label: DisplayText};
type ComparisonItem = {order: number; label: DisplayText; left_text: DisplayText; right_text: DisplayText};
type DiagramNode = {order: number; node_id: string; label: DisplayText};
type DiagramEdge = {order: number; from_node: string; to_node: string; label: DisplayText};
type ScenePayload = {
  payload_type: "timeline" | "bar" | "comparison" | "diagram" | "image" | "aroll";
  timeline_events: TimelineEvent[]; bar_data_points: BarPoint[];
  comparison_items: ComparisonItem[]; diagram_nodes: DiagramNode[];
  diagram_edges: DiagramEdge[]; image_asset_id: string; capture_region: string;
};
export type Scene = {
  scene_id: string; scene_type: string; duration_frames: number; duration_seconds: number;
  source_material_ids: string[]; source_visual_ids: string[]; on_screen_text: DisplayText[];
  scene_payload: ScenePayload;
};
export type ProductionPlan = {canvas: {width: number; height: number; fps: number}; scenes: Scene[]};

const assetMap = assetMapData as Record<string, string>;
const tokens = profileData.design_tokens;
const clamp = {extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const};

const Heading: React.FC<{scene: Scene}> = ({scene}) => <div style={{
  position: "absolute", left: 96, top: 70, fontFamily: tokens.typography.display,
  fontSize: 58, fontWeight: 900, color: tokens.colors.foreground,
}}>{scene.on_screen_text[0]?.text ?? ""}</div>;

export const TimelineMotion: React.FC<{scene: Scene; still: boolean}> = ({scene, still}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const events = scene.scene_payload.timeline_events;
  const x1 = 180;
  const x2 = 1740;
  return <AbsoluteFill>
    <Heading scene={scene}/>
    <svg width="1920" height="1080" role="img" aria-label="timeline">
      <line data-motion-element="timeline-baseline" x1={x1} y1="540"
        x2={still ? x2 : interpolate(frame, [0.1 * fps, 0.8 * fps], [x1, x2], {...clamp, easing: Easing.out(Easing.cubic)})}
        y2="540" stroke={tokens.colors.muted} strokeWidth="8"/>
      {events.map((event, index) => {
        const x = events.length === 1 ? 960 : x1 + index * (x2 - x1) / (events.length - 1);
        const start = (0.75 + index * 0.28) * fps;
        const progress = still ? 1 : interpolate(frame, [start, start + 0.42 * fps], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
        return <g key={event.order} data-motion-element="timeline-marker" opacity={progress}>
          <circle cx={x} cy="540" r={10 + 16 * progress} fill={tokens.colors.accent}/>
          <text x={x} y="470" textAnchor="middle" fill={tokens.colors.accent} fontFamily={tokens.typography.data} fontSize="28">{event.date.text}</text>
          <foreignObject x={x - 180} y="595" width="360" height="170">
            <div style={{fontFamily: tokens.typography.body, fontSize: 30, lineHeight: 1.35, textAlign: "center", color: tokens.colors.foreground}}>{event.label.text}</div>
          </foreignObject>
        </g>;
      })}
    </svg>
  </AbsoluteFill>;
};

export const BarMotion: React.FC<{scene: Scene; still: boolean}> = ({scene, still}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const points = scene.scene_payload.bar_data_points;
  const max = Math.max(1, ...points.map((point) => Math.abs(point.value)));
  return <AbsoluteFill><Heading scene={scene}/><svg width="1920" height="1080" role="img" aria-label="bar chart">
    <line x1="180" y1="850" x2="1740" y2="850" stroke={tokens.colors.muted} strokeWidth="5"/>
    {points.map((point, index) => {
      const slot = 1420 / Math.max(1, points.length);
      const width = Math.min(230, slot * 0.58);
      const x = 250 + index * slot + (slot - width) / 2;
      const finalHeight = 510 * Math.abs(point.value) / max;
      const start = (0.25 + index * 0.22) * fps;
      const progress = still ? 1 : interpolate(frame, [start, start + 0.65 * fps], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
      const textOpacity = still ? 1 : interpolate(frame, [start + 0.45 * fps, start + 0.75 * fps], [0, 1], clamp);
      return <g key={point.order} data-motion-element="bar">
        <rect x={x} y={850 - finalHeight * progress} width={width} height={finalHeight * progress} rx="10" fill={tokens.colors.accent}/>
        <text x={x + width / 2} y={820 - finalHeight} textAnchor="middle" opacity={textOpacity} fill={tokens.colors.foreground} fontFamily={tokens.typography.data} fontSize="30">{point.value_label.text}</text>
        <text x={x + width / 2} y="905" textAnchor="middle" opacity={textOpacity} fill={tokens.colors.foreground} fontFamily={tokens.typography.body} fontSize="30">{point.label.text}</text>
      </g>;
    })}
  </svg></AbsoluteFill>;
};

export const ComparisonMotion: React.FC<{scene: Scene; still: boolean}> = ({scene, still}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return <AbsoluteFill><Heading scene={scene}/><div style={{position: "absolute", left: 120, right: 120, top: 210, bottom: 110, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 34}}>
    {scene.scene_payload.comparison_items.map((item, index) => {
      const start = (0.25 + index * 0.2) * fps;
      const progress = still ? 1 : interpolate(frame, [start, start + 0.5 * fps], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
      return <div key={item.order} data-motion-element="comparison-item" style={{gridColumn: "1 / span 2", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 34, opacity: progress, translate: `${(1 - progress) * 44}px 0`}}>
        <div style={{padding: 28, background: tokens.colors.surface, borderLeft: `8px solid ${tokens.colors.accent}`, fontSize: 31}}><strong>{item.label.text}</strong><br/>{item.left_text.text}</div>
        <div style={{padding: 28, background: tokens.colors.surface, borderLeft: `8px solid ${tokens.colors.muted}`, fontSize: 31}}><strong>{item.label.text}</strong><br/>{item.right_text.text}</div>
      </div>;
    })}
  </div></AbsoluteFill>;
};

export const DiagramMotion: React.FC<{scene: Scene; still: boolean}> = ({scene, still}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const nodes = scene.scene_payload.diagram_nodes;
  const positions = Object.fromEntries(nodes.map((node, index) => [node.node_id, {x: 330 + index * (1260 / Math.max(1, nodes.length - 1)), y: 550 + (index % 2 ? 120 : -120)}]));
  return <AbsoluteFill><Heading scene={scene}/><svg width="1920" height="1080" role="img" aria-label="diagram">
    {scene.scene_payload.diagram_edges.map((edge) => {
      const from = positions[edge.from_node]; const to = positions[edge.to_node];
      const endpointOrder = Math.max(nodes.find((n) => n.node_id === edge.from_node)?.order ?? 1, nodes.find((n) => n.node_id === edge.to_node)?.order ?? 1);
      const start = (0.4 + endpointOrder * 0.26 + edge.order * 0.18) * fps;
      const progress = still ? 1 : interpolate(frame, [start, start + 0.45 * fps], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
      return <g key={edge.order} data-motion-element="diagram-edge" opacity={progress}>
        <line x1={from.x} y1={from.y} x2={from.x + (to.x - from.x) * progress} y2={from.y + (to.y - from.y) * progress} stroke={tokens.colors.muted} strokeWidth="6"/>
        <text x={(from.x + to.x) / 2} y={(from.y + to.y) / 2 - 20} textAnchor="middle" fill={tokens.colors.foreground} fontSize="26">{edge.label.text}</text>
      </g>;
    })}
    {nodes.map((node, index) => {
      const position = positions[node.node_id]; const start = (0.25 + index * 0.26) * fps;
      const progress = still ? 1 : interpolate(frame, [start, start + 0.4 * fps], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
      return <g key={node.node_id} data-motion-element="diagram-node" opacity={progress}>
        <rect x={position.x - 150} y={position.y - 65} width="300" height="130" rx="18" fill={tokens.colors.surface} stroke={tokens.colors.accent} strokeWidth="5"/>
        <text x={position.x} y={position.y + 10} textAnchor="middle" fill={tokens.colors.foreground} fontSize="29">{node.label.text}</text>
      </g>;
    })}
  </svg></AbsoluteFill>;
};

const ImageMotion: React.FC<{scene: Scene; still: boolean}> = ({scene, still}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const asset = assetMap[scene.scene_payload.image_asset_id];
  const progress = still ? 1 : interpolate(frame, [0, Math.min(3 * fps, scene.duration_frames - 1)], [0, 1], clamp);
  return <AbsoluteFill>{asset ? <CanvasImage src={staticFile(asset)} style={{position: "absolute", width: "100%", height: "100%", objectFit: "contain", scale: 1 + progress * 0.035, translate: `${progress * -12}px 0`}}/> : null}<Heading scene={scene}/>{scene.scene_payload.capture_region ? <div data-motion-element="capture-highlight" style={{position: "absolute", left: 180, right: 180, bottom: 130, border: `4px solid ${tokens.colors.accent}`, height: 180, opacity: progress}}/> : null}</AbsoluteFill>;
};

const Aroll: React.FC<{scene: Scene; still: boolean}> = ({scene, still}) => {
  const frame = useCurrentFrame(); const {fps} = useVideoConfig();
  const opacity = still ? 1 : interpolate(frame, [0.1 * fps, 0.6 * fps], [0, 1], clamp);
  return <AbsoluteFill style={{alignItems: "center", justifyContent: "center", background: tokens.colors.surface, opacity}}><div style={{fontFamily: tokens.typography.display, fontSize: 86, fontWeight: 900}}>{scene.on_screen_text[0]?.text ?? "真人口播"}</div></AbsoluteFill>;
};

const SceneBody: React.FC<{scene: Scene; still?: boolean}> = ({scene, still = false}) => <AbsoluteFill style={{backgroundColor: tokens.colors.background, color: tokens.colors.foreground}}>
  {scene.scene_payload.payload_type === "timeline" ? <TimelineMotion scene={scene} still={still}/> : null}
  {scene.scene_payload.payload_type === "bar" ? <BarMotion scene={scene} still={still}/> : null}
  {scene.scene_payload.payload_type === "comparison" ? <ComparisonMotion scene={scene} still={still}/> : null}
  {scene.scene_payload.payload_type === "diagram" ? <DiagramMotion scene={scene} still={still}/> : null}
  {scene.scene_payload.payload_type === "image" ? <ImageMotion scene={scene} still={still}/> : null}
  {scene.scene_payload.payload_type === "aroll" ? <Aroll scene={scene} still={still}/> : null}
</AbsoluteFill>;

export const ProductionScene: React.FC<{scene: Scene}> = ({scene}) => <SceneBody scene={scene}/>;
export const RoughPreview: React.FC<{plan: ProductionPlan}> = ({plan}) => {
  let cursor = 0;
  return <AbsoluteFill>{plan.scenes.map((scene) => {const from = cursor; cursor += scene.duration_frames; return <Sequence key={scene.scene_id} from={from} durationInFrames={scene.duration_frames} name={scene.scene_id}><SceneBody scene={scene}/></Sequence>;})}</AbsoluteFill>;
};
export const HeroStill: React.FC<{scene: Scene}> = ({scene}) => <SceneBody scene={scene} still/>;
