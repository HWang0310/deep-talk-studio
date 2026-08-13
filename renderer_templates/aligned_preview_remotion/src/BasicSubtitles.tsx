import {useCurrentFrame,useVideoConfig} from "remotion";

export type SubtitleCue={cue_id:string;in_seconds:string;out_seconds:string;text:string};
export type SubtitleProfile={subtitle_region_top_px:number;subtitle_region_bottom_px:number;max_lines:number;max_chars_per_line:number;font_size_px:number;line_height_ratio:string;plate_opacity:string;horizontal_padding_px:number;vertical_padding_px:number;text_color:string;plate_color:string};

const wrap=(text:string,max:number)=>{
 const chars=Array.from(text);const lines:string[]=[];
 while(chars.length>0)lines.push(chars.splice(0,max).join(""));
 return lines.join("\n");
};

export const BasicSubtitles:React.FC<{cues:SubtitleCue[];profile:SubtitleProfile}>=({cues,profile})=>{
 const frame=useCurrentFrame();const {fps}=useVideoConfig();const now=frame/fps;
 const cue=cues.find((item)=>now>=Number(item.in_seconds)&&now<Number(item.out_seconds));
 if(!cue)return null;
 return <div className="subtitle-region" style={{top:profile.subtitle_region_top_px,height:profile.subtitle_region_bottom_px-profile.subtitle_region_top_px,color:profile.text_color,fontSize:profile.font_size_px,lineHeight:Number(profile.line_height_ratio)}}>
  <div className="subtitle-plate" style={{backgroundColor:profile.plate_color,opacity:Number(profile.plate_opacity),padding:`${profile.vertical_padding_px}px ${profile.horizontal_padding_px}px`}}>
   {wrap(cue.text,profile.max_chars_per_line)}
  </div>
 </div>;
};
