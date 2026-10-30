/** Everything drawn in image space: photo (or synthetic wall), holds, annotations, climber. */
import { Img } from "remotion";
import { ACCENT, CHALK, holdColor, LIMB_COLORS } from "../palette";
import { poseAt } from "../pose";
import type { Annotation, MotionSpec, Point } from "../spec";
import { segmentAt } from "../timeline";
import { Climber } from "./Climber";

type Props = { spec: MotionSpec; imageSrc: string | null; frame: number };

const TRAIL_STEPS = [2, 4, 6, 8];

export const Scene: React.FC<Props> = ({ spec, imageSrc, frame }) => {
  const { width, height } = spec.image;
  const { index, progress } = segmentAt(spec, frame);
  const keyframe = spec.keyframes[index];
  const holds = new Map(spec.holds.map((h) => [h.id, h]));
  const pose = poseAt(spec, frame);
  const fadeIn = Math.min(1, frame / 12);
  const pulse = 0.5 + 0.5 * Math.sin(frame / 4);

  return (
    <>
      {imageSrc ? (
        <Img src={imageSrc} style={{ position: "absolute", width, height }} />
      ) : (
        <SyntheticWall spec={spec} />
      )}
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ position: "absolute", left: 0, top: 0 }}
      >
        <title>route</title>
        {spec.holds.map((h) => (
          <circle
            key={h.id}
            cx={h.center.x}
            cy={h.center.y}
            r={h.radius + 6}
            fill="none"
            stroke={CHALK}
            strokeOpacity={h.role === "route" ? 0.35 : 0.8}
            strokeWidth={h.role === "route" ? 2 : 4}
            strokeDasharray={h.role === "top" ? "10 6" : undefined}
          />
        ))}
        {keyframe?.annotations.map((a, i) => (
          <AnnotationMark
            // biome-ignore lint/suspicious/noArrayIndexKey: annotations have no identity
            key={i}
            annotation={a}
            holds={holds}
            progress={progress}
            pulse={pulse}
          />
        ))}
        {keyframe?.limb &&
          keyframe.annotations.some((a) => a.kind === "trail") &&
          progress < 1 &&
          TRAIL_STEPS.map((step, i) => {
            const ghost = poseAt(spec, frame - step).limbs[keyframe.limb ?? "lh"].end;
            return (
              <circle
                key={step}
                cx={ghost.x}
                cy={ghost.y}
                r={spec.body.shoulder_width * 0.09}
                fill={LIMB_COLORS[keyframe.limb ?? "lh"]}
                opacity={0.45 - i * 0.1}
              />
            );
          })}
        <g opacity={fadeIn}>
          <Climber pose={pose} body={spec.body} />
        </g>
      </svg>
    </>
  );
};

const SyntheticWall: React.FC<{ spec: MotionSpec }> = ({ spec }) => {
  const { width, height } = spec.image;
  return (
    <svg width={width} height={height} style={{ position: "absolute", left: 0, top: 0 }}>
      <title>synthetic wall</title>
      <defs>
        <pattern id="tnuts" width="50" height="50" patternUnits="userSpaceOnUse">
          <circle cx="25" cy="25" r="3" fill="#5c5c5a" />
        </pattern>
      </defs>
      <rect width={width} height={height} fill="#96968f" />
      <rect width={width} height={height} fill="url(#tnuts)" />
      {spec.holds.map((h) => (
        <circle key={h.id} cx={h.center.x} cy={h.center.y} r={h.radius} fill={holdColor(h.color)} />
      ))}
    </svg>
  );
};

type MarkProps = {
  annotation: Annotation;
  holds: Map<number, { center: Point; radius: number }>;
  progress: number;
  pulse: number;
};

const AnnotationMark: React.FC<MarkProps> = ({ annotation, holds, progress, pulse }) => {
  switch (annotation.kind) {
    case "highlight": {
      const h = holds.get(annotation.hold_id);
      if (!h) return null;
      return (
        <circle
          cx={h.center.x}
          cy={h.center.y}
          r={h.radius + 12 + pulse * 6}
          fill="none"
          stroke={annotation.color ?? ACCENT}
          strokeWidth={6}
          opacity={0.9}
        />
      );
    }
    case "arrow": {
      const to = holds.get(annotation.to_hold_id);
      const from =
        annotation.from_hold_id === null ? undefined : holds.get(annotation.from_hold_id);
      if (!to || !from) return null;
      const length = Math.hypot(to.center.x - from.center.x, to.center.y - from.center.y);
      const drawn = Math.min(1, progress * 1.6);
      return (
        <line
          x1={from.center.x}
          y1={from.center.y}
          x2={to.center.x}
          y2={to.center.y}
          stroke={LIMB_COLORS[annotation.limb]}
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={`${length} ${length}`}
          strokeDashoffset={length * (1 - drawn)}
          opacity={0.85 * (1 - Math.max(0, progress - 0.8) * 5)}
        />
      );
    }
    default:
      return null; // captions, callouts and trails are drawn elsewhere
  }
};
