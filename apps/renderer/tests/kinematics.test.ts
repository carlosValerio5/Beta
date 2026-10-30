import { describe, expect, it } from "vitest";
import { BEND, limbRoots, solveTwoBone, TORSO_BLEND } from "../src/kinematics";
import type { BodyModel, Limb, Point } from "../src/spec";
import { readContract } from "./fixtures";

type TwoBoneCase = {
  root: Point;
  target: Point;
  l1: number;
  l2: number;
  bend: number;
  joint: Point;
  end: Point;
  reached: boolean;
};
type RootsCase = { hip: Point; hand_targets: Point[]; roots: Record<Limb, Point> };
type Fixtures = {
  torso_blend: number;
  bend: Record<Limb, number>;
  body: BodyModel;
  two_bone: TwoBoneCase[];
  limb_roots: RootsCase[];
};

const fixtures = readContract("kinematics/fixtures.json") as Fixtures;

function close(actual: Point, expected: Point): void {
  expect(actual.x).toBeCloseTo(expected.x, 5);
  expect(actual.y).toBeCloseTo(expected.y, 5);
}

describe("kinematics matches the Python reference", () => {
  it("uses the same constants", () => {
    expect(TORSO_BLEND).toBe(fixtures.torso_blend);
    expect(BEND).toEqual(fixtures.bend);
  });

  it.each(fixtures.two_bone)("solveTwoBone %#", (c) => {
    const sol = solveTwoBone(c.root, c.target, c.l1, c.l2, c.bend);
    close(sol.joint, c.joint);
    close(sol.end, c.end);
    expect(sol.reached).toBe(c.reached);
  });

  it.each(fixtures.limb_roots)("limbRoots %#", (c) => {
    const roots = limbRoots(c.hip, fixtures.body, c.hand_targets);
    for (const limb of ["lh", "rh", "lf", "rf"] as const) {
      close(roots[limb], c.roots[limb]);
    }
  });
});
