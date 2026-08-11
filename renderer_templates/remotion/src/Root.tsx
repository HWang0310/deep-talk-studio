import {Composition, Still} from "remotion";
import planData from "./production-plan.json";
import {HeroStill, ProductionScene, RoughPreview, type ProductionPlan, type Scene} from "./ProductionComposition";

const plan = planData as ProductionPlan;

export const RemotionRoot: React.FC = () => {
  const finalScene = plan.scenes[plan.scenes.length - 1];
  return <>
    {plan.scenes.map((scene: Scene) => <Composition
      key={scene.scene_id}
      id={`Scene-${scene.scene_id}`}
      component={ProductionScene}
      defaultProps={{scene}}
      durationInFrames={scene.duration_frames}
      fps={plan.canvas.fps}
      width={plan.canvas.width}
      height={plan.canvas.height}
    />)}
    <Composition
      id="RoughPreview"
      component={RoughPreview}
      defaultProps={{plan}}
      durationInFrames={plan.scenes.reduce((sum, scene) => sum + scene.duration_frames, 0)}
      fps={plan.canvas.fps}
      width={plan.canvas.width}
      height={plan.canvas.height}
    />
    <Still
      id="HeroStill"
      component={HeroStill}
      defaultProps={{scene: finalScene}}
      width={plan.canvas.width}
      height={plan.canvas.height}
    />
  </>;
};
