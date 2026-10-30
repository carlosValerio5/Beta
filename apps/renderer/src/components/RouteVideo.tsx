import { AbsoluteFill, useCurrentFrame } from "remotion";
import { INK } from "../palette";
import type { MotionSpec } from "../spec";
import { cameraAt, sceneTransform } from "../timeline";
import { Hud } from "./Hud";
import { Scene } from "./Scene";

export type RouteVideoProps = {
  spec: MotionSpec;
  /** data: URL of the normalised photo; null draws a synthetic wall from the spec's holds. */
  imageSrc: string | null;
};

export const RouteVideo: React.FC<RouteVideoProps> = ({ spec, imageSrc }) => {
  const frame = useCurrentFrame();
  const transform = sceneTransform(cameraAt(spec, frame), spec.image, spec.meta);
  return (
    <AbsoluteFill style={{ backgroundColor: INK, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: spec.image.width,
          height: spec.image.height,
          transformOrigin: "0 0",
          transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`,
        }}
      >
        <Scene spec={spec} imageSrc={imageSrc} frame={frame} />
      </div>
      <Hud spec={spec} frame={frame} transform={transform} />
    </AbsoluteFill>
  );
};
