import { describe, expect, it } from "vitest";
import { parseMotionSpec } from "../src/spec";
import { exampleNames, readContract } from "./fixtures";

describe("MotionSpec schema mirror", () => {
  it.each(exampleNames())("parses contract example %s", (name) => {
    const spec = parseMotionSpec(readContract(`motion-spec/examples/${name}`));
    expect(spec.version).toBe("1");
    expect(spec.keyframes.length).toBeGreaterThan(1);
    expect(spec.chapters.length).toBe(spec.keyframes.length - 1);
  });

  it("rejects unknown annotation kinds", () => {
    const raw = structuredClone(readContract("motion-spec/examples/ladder.json")) as {
      keyframes: { annotations: unknown[] }[];
    };
    raw.keyframes[1]?.annotations.push({ kind: "fireworks" });
    expect(() => parseMotionSpec(raw)).toThrow(/annotation|kind|invalid/i);
  });

  it("rejects unexpected keys like the Python model does", () => {
    const raw = { ...(readContract("motion-spec/examples/ladder.json") as object), extra: 1 };
    expect(() => parseMotionSpec(raw)).toThrow();
  });

  it("explains what is wrong", () => {
    expect(() => parseMotionSpec({ version: "1" })).toThrow(/MotionSpec/);
  });
});
