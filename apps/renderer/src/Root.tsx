import { type CalculateMetadataFunction, Composition } from "remotion";
import fixture from "../../../contracts/motion-spec/examples/ladder-directed.json";
import { RouteVideo, type RouteVideoProps } from "./components/RouteVideo";
import { parseMotionSpec } from "./spec";

const defaultSpec = parseMotionSpec(fixture);

const calculateMetadata: CalculateMetadataFunction<RouteVideoProps> = ({ props }) => ({
  durationInFrames: props.spec.meta.duration_frames,
  fps: props.spec.meta.fps,
  width: props.spec.meta.width,
  height: props.spec.meta.height,
});

export const Root: React.FC = () => (
  <Composition
    id="RouteVideo"
    component={RouteVideo}
    defaultProps={{ spec: defaultSpec, imageSrc: null } satisfies RouteVideoProps}
    durationInFrames={defaultSpec.meta.duration_frames}
    fps={defaultSpec.meta.fps}
    width={defaultSpec.meta.width}
    height={defaultSpec.meta.height}
    calculateMetadata={calculateMetadata}
  />
);
