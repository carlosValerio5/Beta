import { describe, expect, it } from "vitest";
import { parseMotionSpec } from "../src/spec";
import { cameraAt, chapterAt, EASINGS, ease, sceneTransform, segmentAt } from "../src/timeline";
import { readContract } from "./fixtures";

const spec = parseMotionSpec(readContract("motion-spec/examples/ladder-directed.json"));

describe("easing", () => {
  it.each(Object.keys(EASINGS))("%s goes 0 -> 1 monotonically", (name) => {
    const e = name as keyof typeof EASINGS;
    expect(ease(e, 0)).toBeCloseTo(0);
    expect(ease(e, 1)).toBeCloseTo(1);
    let last = 0;
    for (let t = 0; t <= 1.0001; t += 0.05) {
      const v = ease(e, Math.min(t, 1));
      expect(v).toBeGreaterThanOrEqual(last - 1e-9);
      last = v;
    }
  });

  it("clamps out-of-range input", () => {
    expect(ease("linear", -1)).toBe(0);
    expect(ease("linear", 2)).toBe(1);
  });
});

describe("segmentAt", () => {
  it("starts at the opening pose", () => {
    expect(segmentAt(spec, 0)).toEqual({ index: 0, progress: 0 });
  });

  it("finds a segment by its start frame", () => {
    const k = spec.keyframes[3];
    expect(segmentAt(spec, k?.start_frame ?? -1)).toEqual({ index: 3, progress: 0 });
  });

  it("holds the last pose through the outro", () => {
    const last = spec.keyframes.length - 1;
    expect(segmentAt(spec, spec.meta.duration_frames - 1)).toEqual({ index: last, progress: 1 });
  });
});

describe("camera", () => {
  it("reaches each keyframe's camera at the end of its segment", () => {
    const k = spec.keyframes[2];
    if (!k) throw new Error("fixture too short");
    const cam = cameraAt(spec, k.start_frame + k.duration_frames - 1 + 1);
    expect(cam.center.x).toBeCloseTo(k.camera.center.x, 0);
    expect(cam.zoom).toBeCloseTo(k.camera.zoom, 1);
  });

  it("fits the whole image at zoom 1 and centres the camera", () => {
    const t = sceneTransform(
      { center: { x: 500, y: 750 }, zoom: 1 },
      { width: 1000, height: 1500 },
      { width: 1080, height: 1920 },
    );
    expect(1000 * t.scale).toBeLessThanOrEqual(1080 + 1e-6);
    expect(1500 * t.scale).toBeLessThanOrEqual(1920 + 1e-6);
    expect(500 * t.scale + t.x).toBeCloseTo(540);
    expect(750 * t.scale + t.y).toBeCloseTo(960);
  });

  it("never pans past the image edge when zoomed in", () => {
    const t = sceneTransform(
      { center: { x: 0, y: 0 }, zoom: 2.5 },
      { width: 1000, height: 1500 },
      { width: 1080, height: 1920 },
    );
    expect(t.x).toBeLessThanOrEqual(0);
    expect(t.y).toBeLessThanOrEqual(0);
  });
});

describe("chapters", () => {
  it("is null on the opening pose and names moves after", () => {
    expect(chapterAt(spec, 0)).toBeNull();
    const second = spec.chapters[1];
    expect(chapterAt(spec, second?.start_frame ?? 0)?.move_index).toBe(1);
  });
});
