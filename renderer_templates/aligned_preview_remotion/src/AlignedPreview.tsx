import {Video} from "@remotion/media";
import {AbsoluteFill,Img,Sequence,staticFile} from "remotion";
type Placement={placement_id:string;source_kind:"clean_aroll"|"real_image"|"real_video"|"original_motion";asset_path:string;preview_in_frame:number;preview_out_frame:number|null;source_clip_in_seconds?:string};
export type AlignedPreviewProps={media_duration_seconds:string;placements:Placement[]};
export const AlignedPreview:React.FC<AlignedPreviewProps>=({placements})=>{
 const ar=placements.find((p)=>p.source_kind==="clean_aroll"); if(!ar)throw new Error("missing layer 0 clean A-roll");
 return <AbsoluteFill className="canvas">
  {/* layer 0: canonical Clean A-roll stays visible whenever no ready overlay is active */}
  <Video src={staticFile(ar.asset_path)} muted className="contained"/>
  {placements.filter((p)=>p.source_kind!=="clean_aroll").map((p)=>{
   const duration=Math.max(1,(p.preview_out_frame??p.preview_in_frame+1)-p.preview_in_frame);
   return <Sequence key={p.placement_id} from={p.preview_in_frame} durationInFrames={duration}>
    {p.source_kind==="real_image"?<Img src={staticFile(p.asset_path)} className="contained"/>:<Video src={staticFile(p.asset_path)} muted trimBefore={Math.ceil(Number(p.source_clip_in_seconds||0)*30)} className="contained"/>}
   </Sequence>;
  })}
 </AbsoluteFill>;
};
