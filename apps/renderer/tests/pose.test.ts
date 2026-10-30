import { describe, expect, it } from "vitest";
import { poseAt } from "../src/pose";
import { type Limb, parseMotionSpec, type Point } from "../src/spec";
import { readContract } from "./fixtures";

const spec = parseMotionSpec(readContract("motion-spec/examples/ladder-directed.json"));
const holds = new Map(spec.holds.map((h) => [h.id, h.center]));
const LIMBS: Limb[] = ["lh", "rh", "lf", "rf"];

function dist(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

describe("poseAt", () => {
  it("puts every contacted limb on its hold when a segment completes", () => {
    for (let i = 0; i < spec.keyframes.length - 1; i++) {
      const done = spec.keyframes[i];
      const next = spec.keyframes[i + 1];
      if (!done || !next) continue;
      const pose = poseAt(spec, next.start_frame);
      for (const limb of LIMBS) {
        const hold = done.contacts[limb];
        if (hold === null) continue;
        const target = holds.get(hold);
        if (!target) throw new Error(`missing hold ${hold}`);
        expect(dist(pose.limbs[limb].end, target)).toBeLessThan(1);
      }
    }
  });

  it("keeps segment lengths when a limb reaches", () => {
    const pose = poseAt(spec, spec.keyframes[4]?.start_frame ?? 0);
    const arm = pose.limbs.lh;
    expect(dist(arm.root, arm.joint)).toBeCloseTo(spec.body.upper_arm, 3);
    expect(dist(arm.joint, arm.end)).toBeCloseTo(spec.body.forearm, 3);
  });

  it("moves the active limb between its old and new hold mid-segment", () => {
    const k = spec.keyframes[1];
    const prev = spec.keyframes[0];
    if (!k || !prev || !k.limb) throw new Error("fixture shape changed");
    const from = holds.get(prev.contacts[k.limb] ?? -1);
    const to = holds.get(k.contacts[k.limb] ?? -1);
    if (!from || !to) throw new Error("fixture shape changed");
    const mid = poseAt(spec, k.start_frame + Math.floor(k.duration_frames / 2)).limbs[k.limb].end;
    expect(dist(mid, from)).toBeGreaterThan(5);
    expect(dist(mid, to)).toBeGreaterThan(5);
  });

  it("puts the head above the shoulders", () => {
    const pose = poseAt(spec, 0);
    const shoulders = (pose.limbs.lh.root.y + pose.limbs.rh.root.y) / 2;
    expect(pose.head.y).toBeLessThan(shoulders);
  });
});
