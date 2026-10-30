/** Time → segment, easing, camera and the image→screen transform. Pure functions. */
import type { Camera, Easing, MotionSpec, Point } from "./spec";

export const EASINGS: Record<Easing, (t: number) => number> = {
  linear: (t) => t,
  ease_in_out: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
  ease_out: (t) => 1 - (1 - t) ** 2,
  snap: (t) => 1 - (1 - t) ** 4,
};

export function clamp01(t: number): number {
  return Math.min(1, Math.max(0, t));
}

export function ease(name: Easing, t: number): number {
  return EASINGS[name](clamp01(t));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function lerpPoint(a: Point, b: Point, t: number): Point {
  return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) };
}

export type Segment = { index: number; progress: number };

/** Which keyframe segment is playing at `frame`; after the last one the final pose holds. */
export function segmentAt(spec: MotionSpec, frame: number): Segment {
  for (const [index, k] of spec.keyframes.entries()) {
    if (frame < k.start_frame + k.duration_frames) {
      return { index, progress: clamp01((frame - k.start_frame) / k.duration_frames) };
    }
  }
  return { index: spec.keyframes.length - 1, progress: 1 };
}

export function keyframePair(spec: MotionSpec, index: number) {
  const current = spec.keyframes[index];
  const previous = spec.keyframes[Math.max(index - 1, 0)];
  if (!current || !previous) throw new Error(`keyframe ${index} out of range`);
  return { previous, current };
}

export function cameraAt(spec: MotionSpec, frame: number): Camera {
  const { index, progress } = segmentAt(spec, frame);
  const { previous, current } = keyframePair(spec, index);
  const t = ease("ease_in_out", progress);
  return {
    center: lerpPoint(previous.camera.center, current.camera.center, t),
    zoom: lerp(previous.camera.zoom, current.camera.zoom, t),
  };
}

export type Size = { width: number; height: number };
export type Transform = { scale: number; x: number; y: number };

/** Image-space → screen-space. Zoom 1 = whole image visible; never pans past an image edge. */
export function sceneTransform(camera: Camera, image: Size, output: Size): Transform {
  const base = Math.min(output.width / image.width, output.height / image.height);
  const scale = base * camera.zoom;
  const axis = (center: number, imageLen: number, outLen: number) => {
    const scaled = imageLen * scale;
    if (scaled < outLen) return (outLen - scaled) / 2;
    const offset = outLen / 2 - center * scale;
    return Math.min(0, Math.max(outLen - scaled, offset));
  };
  return {
    scale,
    x: axis(camera.center.x, image.width, output.width),
    y: axis(camera.center.y, image.height, output.height),
  };
}

export function toScreen(p: Point, t: Transform): Point {
  return { x: p.x * t.scale + t.x, y: p.y * t.scale + t.y };
}

export function chapterAt(spec: MotionSpec, frame: number) {
  const { index } = segmentAt(spec, frame);
  const k = spec.keyframes[index];
  if (!k || k.move_index < 0) return null;
  return spec.chapters.find((c) => c.move_index === k.move_index) ?? null;
}

/** 0 → 1 → 0 envelope for text that fades in after `inFrames` and out over the last `outFrames`. */
export function fadeEnvelope(
  frame: number,
  start: number,
  duration: number,
  inFrames = 6,
  outFrames = 4,
) {
  const local = frame - start;
  if (local < 0 || local >= duration) return 0;
  return Math.min(clamp01(local / inFrames), clamp01((duration - local) / outFrames));
}
