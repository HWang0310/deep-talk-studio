import {Video} from "@remotion/media";
import {AbsoluteFill,Img,Sequence,staticFile} from "remotion";
import {BasicSubtitles,SubtitleCue,SubtitleProfile} from "./BasicSubtitles";
type Placement={placement_id:string;source_kind:"clean_aroll"|"real_image"|"real_video"|"original_motion";asset_path:string;preview_in_frame:number;preview_out_frame:number|null;source_clip_in_seconds?:string;presentation_mode?:"primary_visual"|"primary_visual_with_pip"|"supporting_overlay"};
export type AlignedPreviewProps={media_duration_seconds:string;placements:Placement[];subtitle_cues:SubtitleCue[];subtitle_profile:SubtitleProfile;subtitle_artifact_digest:string;subtitles_enabled:boolean};
export const AlignedPreview:React.FC<AlignedPreviewProps>=({placements,subtitle_cues,subtitle_profile,subtitles_enabled})=>{
 const ar=placements.find((p)=>p.source_kind==="clean_aroll"); if(!ar)throw new Error("missing layer 0 clean A-roll");
 return <AbsoluteFill className="canvas">
  {/* layer 0: canonical Clean A-roll stays visible whenever no ready overlay is active */}
  <Video src={staticFile(ar.asset_path)} muted className="contained"/>
  <div className="content-safe-region">{placements.filter((p)=>p.source_kind!=="clean_aroll").map((p)=>{
   const duration=Math.max(1,(p.preview_out_frame??p.preview_in_frame+1)-p.preview_in_frame);
   return <Sequence key={p.placement_id} from={p.preview_in_frame} durationInFrames={duration} className={p.presentation_mode||"supporting_overlay"}>
    {p.source_kind==="real_image"?<Img src={staticFile(p.asset_path)} className="contained"/>:<Video src={staticFile(p.asset_path)} muted trimBefore={Math.ceil(Number(p.source_clip_in_seconds||0)*30)} className="contained"/>}
    {p.presentation_mode==="primary_visual_with_pip"?<Video src={staticFile(ar.asset_path)} muted className="aroll-pip"/>:null}
   </Sequence>;
  })}</div>
  {subtitles_enabled?<BasicSubtitles cues={subtitle_cues} profile={subtitle_profile}/>:null}
 </AbsoluteFill>;
};
