/**
 * Port of `beta_core.kinematics`. Must stay numerically identical: see
 * tests/kinematics.test.ts and contracts/kinematics/fixtures.json.
 */
import type { BodyModel, Limb, Point } from "./spec";

export const TORSO_BLEND = 0.5;
export const BEND: Record<Limb, number> = { lh: -1, rh: 1, lf: 1, rf: -1 };

const EPS = 1e-9;
const UP: [number, number] = [0, -1];

export type IKSolution = { joint: Point; end: Point; reached: boolean };

function unit(dx: number, dy: number): [number, number] {
  const n = Math.hypot(dx, dy);
  return n < EPS ? UP : [dx / n, dy / n];
}

export function isHand(limb: Limb): boolean {
  return limb === "lh" || limb === "rh";
}

export function torsoAxis(hip: Point, handTargets: readonly Point[]): [number, number] {
  if (handTargets.length === 0) return UP;
  const mx = handTargets.reduce((s, p) => s + p.x, 0) / handTargets.length;
  const my = handTargets.reduce((s, p) => s + p.y, 0) / handTargets.length;
  const [vx, vy] = unit(mx - hip.x, my - hip.y);
  return unit(
    TORSO_BLEND * vx + (1 - TORSO_BLEND) * UP[0],
    TORSO_BLEND * vy + (1 - TORSO_BLEND) * UP[1],
  );
}

export function limbRoots(
  hip: Point,
  body: BodyModel,
  handTargets: readonly Point[],
): Record<Limb, Point> {
  const [ax, ay] = torsoAxis(hip, handTargets);
  const [px, py] = [-ay, ax];
  const sx = hip.x + ax * body.torso;
  const sy = hip.y + ay * body.torso;
  const hs = body.shoulder_width / 2;
  const hh = body.hip_width / 2;
  return {
    lh: { x: sx - px * hs, y: sy - py * hs },
    rh: { x: sx + px * hs, y: sy + py * hs },
    lf: { x: hip.x - px * hh, y: hip.y - py * hh },
    rf: { x: hip.x + px * hh, y: hip.y + py * hh },
  };
}

export function segmentLengths(body: BodyModel, limb: Limb): [number, number] {
  return isHand(limb) ? [body.upper_arm, body.forearm] : [body.thigh, body.shin];
}

export function solveTwoBone(
  root: Point,
  target: Point,
  l1: number,
  l2: number,
  bend: number,
): IKSolution {
  const dx = target.x - root.x;
  const dy = target.y - root.y;
  const d = Math.hypot(dx, dy);
  const [ux, uy] = unit(dx, dy);
  const reach = l1 + l2;
  if (d >= reach) {
    const joint = { x: root.x + ux * l1, y: root.y + uy * l1 };
    const reached = d <= reach + EPS;
    const end = reached ? target : { x: root.x + ux * reach, y: root.y + uy * reach };
    return { joint, end, reached };
  }
  const minReach = Math.abs(l1 - l2);
  const dd = Math.max(d, minReach);
  const a = dd > EPS ? (l1 * l1 - l2 * l2 + dd * dd) / (2 * dd) : 0;
  const h = Math.sqrt(Math.max(l1 * l1 - a * a, 0));
  const [px, py] = [-uy, ux];
  const joint = { x: root.x + ux * a + px * h * bend, y: root.y + uy * a + py * h * bend };
  if (d >= minReach - EPS) return { joint, end: target, reached: true };
  return { joint, end: { x: root.x + ux * dd, y: root.y + uy * dd }, reached: false };
}
