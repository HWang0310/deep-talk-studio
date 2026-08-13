import {CalculateMetadataFunction,Composition} from "remotion";
import bridge from "../public/bridge.json";
import {AlignedPreview,AlignedPreviewProps} from "./AlignedPreview";
const props=bridge as AlignedPreviewProps;
const metadata:CalculateMetadataFunction<AlignedPreviewProps>=({props})=>({durationInFrames:Math.ceil(Number(props.media_duration_seconds)*30)});
export const RemotionRoot:React.FC=()=><Composition id="AlignedPreview" component={AlignedPreview} defaultProps={props} calculateMetadata={metadata} durationInFrames={Math.ceil(Number(props.media_duration_seconds)*30)} fps={30} width={1920} height={1080}/>;
