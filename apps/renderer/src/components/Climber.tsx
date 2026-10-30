import { CHALK, INK, LIMB_COLORS } from "../palette";
import type { Pose } from "../pose";
import type { BodyModel, Limb } from "../spec";

type Props = { pose: Pose; body: BodyModel };

const DRAW_ORDER: Limb[] = ["lf", "rf", "lh", "rh"];

export const Climber: React.FC<Props> = ({ pose, body }) => {
  const limbWidth = body.shoulder_width * 0.12;
  const torsoWidth = body.shoulder_width * 0.26;
  const { lh, rh, lf, rf } = pose.limbs;
  return (
    <g strokeLinecap="round" strokeLinejoin="round">
      {/* soft shadow so the figure reads on busy walls */}
      <g opacity={0.35} transform="translate(6 8)">
        <line
          x1={pose.hip.x}
          y1={pose.hip.y}
          x2={pose.shoulders.x}
          y2={pose.shoulders.y}
          stroke={INK}
          strokeWidth={torsoWidth}
        />
      </g>
      {DRAW_ORDER.filter((l) => l === "lf" || l === "rf").map((limb) => (
        <LimbPath key={limb} limb={limb} pose={pose} width={limbWidth * 1.15} />
      ))}
      <line
        x1={lf.root.x}
        y1={lf.root.y}
        x2={rf.root.x}
        y2={rf.root.y}
        stroke={CHALK}
        strokeWidth={torsoWidth * 0.55}
      />
      <line
        x1={pose.hip.x}
        y1={pose.hip.y}
        x2={pose.shoulders.x}
        y2={pose.shoulders.y}
        stroke={CHALK}
        strokeWidth={torsoWidth}
      />
      <line
        x1={lh.root.x}
        y1={lh.root.y}
        x2={rh.root.x}
        y2={rh.root.y}
        stroke={CHALK}
        strokeWidth={limbWidth * 0.9}
      />
      {DRAW_ORDER.filter((l) => l === "lh" || l === "rh").map((limb) => (
        <LimbPath key={limb} limb={limb} pose={pose} width={limbWidth} />
      ))}
      <circle
        cx={pose.head.x}
        cy={pose.head.y}
        r={body.head_radius}
        fill={CHALK}
        stroke={INK}
        strokeWidth={3}
      />
    </g>
  );
};

const LimbPath: React.FC<{ limb: Limb; pose: Pose; width: number }> = ({ limb, pose, width }) => {
  const p = pose.limbs[limb];
  const color = LIMB_COLORS[limb];
  return (
    <g>
      <polyline
        points={`${p.root.x},${p.root.y} ${p.joint.x},${p.joint.y} ${p.end.x},${p.end.y}`}
        fill="none"
        stroke={INK}
        strokeWidth={width + 6}
        opacity={0.6}
      />
      <polyline
        points={`${p.root.x},${p.root.y} ${p.joint.x},${p.joint.y} ${p.end.x},${p.end.y}`}
        fill="none"
        stroke={color}
        strokeWidth={width}
      />
      <circle
        cx={p.end.x}
        cy={p.end.y}
        r={width * 0.75}
        fill={color}
        stroke={CHALK}
        strokeWidth={p.onHold ? 4 : 0}
      />
    </g>
  );
};
