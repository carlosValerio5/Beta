/**
 * The climber's skeleton at any frame.
 *
 * Within a segment the hip eases from the previous keyframe's hip to the current one. Limb ends
 * stay on their holds, except the moving limb, which travels along a shallow arc (bulging away
 * from the body) from its old hold to its new one. Free limbs hang. Joints come from two-bone IK.
 */
import { BEND, isHand, limbRoots, segmentLengths, solveTwoBone } from "./kinematics";
import { LIMBS, type Limb, type MotionSpec, type Point } from "./spec";
import { ease, keyframePair, lerpPoint, segmentAt } from "./timeline";

export type LimbPose = { root: Point; joint: Point; end: Point; reached: boolean; onHold: boolean };
export type Pose = { hip: Point; shoulders: Point; head: Point; limbs: Record<Limb, LimbPose> };

const ARC_FRACTION = 0.25;
const ARC_MAX_PX = 60;

function restEnd(root: Point, limb: Limb, spec: MotionSpec): Point {
  const side = limb === "lh" || limb === "lf" ? -1 : 1;
  if (isHand(limb)) {
    const len = (spec.body.upper_arm + spec.body.forearm) * 0.85;
    return { x: root.x + side * 0.3 * len, y: root.y + 0.95 * len };
  }
  const len = (spec.body.thigh + spec.body.shin) * 0.95;
  return { x: root.x + side * 0.15 * len, y: root.y + 0.99 * len };
}

/**
 * The validators accept poses needing up to ~108-112% of limb length (real climbers stretch,
 * shift hips and rotate). A hand floating beside its hold reads as wrong, so the figure's limbs
 * stretch up to MAX_STRETCH to keep contact instead.
 */
const MAX_STRETCH = 1.15;

function stretchedLengths(
  spec: MotionSpec,
  limb: Limb,
  root: Point,
  target: Point,
): [number, number] {
  const [l1, l2] = segmentLengths(spec.body, limb);
  const needed = Math.hypot(target.x - root.x, target.y - root.y) / (l1 + l2);
  const factor = Math.min(Math.max(needed, 1), MAX_STRETCH);
  return [l1 * factor, l2 * factor];
}

function arc(from: Point, to: Point, t: number, hip: Point): Point {
  const base = lerpPoint(from, to, t);
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const len = Math.hypot(dx, dy);
  if (len < 1e-6) return base;
  let px = -dy / len;
  let py = dx / len;
  if (px * (base.x - hip.x) + py * (base.y - hip.y) < 0) {
    px = -px;
    py = -py;
  }
  const bulge = Math.sin(Math.PI * t) * Math.min(len * ARC_FRACTION, ARC_MAX_PX);
  return { x: base.x + px * bulge, y: base.y + py * bulge };
}

export function poseAt(spec: MotionSpec, frame: number): Pose {
  const { index, progress } = segmentAt(spec, frame);
  const { previous, current } = keyframePair(spec, index);
  const t = ease(current.easing, progress);
  const holds = new Map(spec.holds.map((h) => [h.id, h.center]));
  const at = (id: number | null) => (id === null ? null : (holds.get(id) ?? null));

  const hip = lerpPoint(previous.hip, current.hip, t);

  // Pass 1: ends that are on (or travelling between) holds.
  const known: Partial<Record<Limb, Point>> = {};
  const pending: Limb[] = [];
  for (const limb of LIMBS) {
    const from = at(previous.contacts[limb]);
    const to = at(current.contacts[limb]);
    if (from && to) {
      known[limb] =
        limb === current.limb && from !== to ? arc(from, to, t, hip) : lerpPoint(from, to, t);
    } else {
      pending.push(limb);
    }
  }

  const handTargets = (["lh", "rh"] as const).flatMap((h) => (known[h] ? [known[h]] : []));
  const roots = limbRoots(hip, spec.body, handTargets);

  // Pass 2: limbs leaving or joining a hold, or hanging free.
  for (const limb of pending) {
    const rest = restEnd(roots[limb], limb, spec);
    const from = at(previous.contacts[limb]) ?? rest;
    const to = at(current.contacts[limb]) ?? rest;
    known[limb] = lerpPoint(from, to, t);
  }

  const limbs = {} as Record<Limb, LimbPose>;
  for (const limb of LIMBS) {
    const target = known[limb] ?? roots[limb];
    const [l1, l2] = stretchedLengths(spec, limb, roots[limb], target);
    const sol = solveTwoBone(roots[limb], target, l1, l2, BEND[limb]);
    // Closer than a folded limb can reach (hand at the shoulder): the IK keeps the end short of the
    // target; for drawing, fold fully and keep the hand/foot on its hold.
    const tooClose =
      !sol.reached && Math.hypot(target.x - roots[limb].x, target.y - roots[limb].y) < l1 + l2;
    const end = tooClose ? target : sol.end;
    const onHold = current.contacts[limb] !== null && (progress >= 1 || limb !== current.limb);
    limbs[limb] = {
      root: roots[limb],
      joint: sol.joint,
      end,
      reached: sol.reached || tooClose,
      onHold,
    };
  }

  const shoulders = lerpPoint(roots.lh, roots.rh, 0.5);
  const axisX = shoulders.x - hip.x;
  const axisY = shoulders.y - hip.y;
  const axisLen = Math.hypot(axisX, axisY) || 1;
  const neck = spec.body.head_radius * 1.6;
  const head = {
    x: shoulders.x + (axisX / axisLen) * neck,
    y: shoulders.y + (axisY / axisLen) * neck,
  };
  return { hip, shoulders, head, limbs };
}
