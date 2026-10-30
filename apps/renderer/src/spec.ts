/**
 * zod mirror of `beta_core.domain.motion.MotionSpec` (contracts/motion-spec/v1.schema.json).
 * Objects are strict, like the Python models (`extra="forbid"`).
 */
import { z } from "zod";

const point = z.strictObject({ x: z.number(), y: z.number() });
const holdId = z.number().int();
export const limbSchema = z.enum(["lh", "rh", "lf", "rf"]);
export const techniqueSchema = z.enum([
  "reach",
  "cross",
  "match",
  "gaston",
  "undercling",
  "sidepull",
  "lock_off",
  "deadpoint",
  "dyno",
  "mantle",
  "flag",
  "drop_knee",
  "heel_hook",
  "toe_hook",
  "high_step",
  "smear",
  "rockover",
  "bump",
  "step",
]);
export const easingSchema = z.enum(["linear", "ease_in_out", "ease_out", "snap"]);

const contacts = z.strictObject({
  lh: holdId.nullable(),
  rh: holdId.nullable(),
  lf: holdId.nullable(),
  rf: holdId.nullable(),
});

const camera = z.strictObject({ center: point, zoom: z.number().min(1).max(4) });

const annotation = z.discriminatedUnion("kind", [
  z.strictObject({ kind: z.literal("highlight"), hold_id: holdId, color: z.string().nullable() }),
  z.strictObject({
    kind: z.literal("arrow"),
    limb: limbSchema,
    from_hold_id: holdId.nullable(),
    to_hold_id: holdId,
  }),
  z.strictObject({ kind: z.literal("caption"), text: z.string().min(1).max(60) }),
  z.strictObject({
    kind: z.literal("callout"),
    text: z.string().min(1).max(40),
    technique: techniqueSchema.nullable(),
    hold_id: holdId.nullable(),
  }),
  z.strictObject({ kind: z.literal("trail"), limb: limbSchema }),
]);

const keyframe = z.strictObject({
  move_index: z.number().int().min(-1),
  start_frame: z.number().int().min(0),
  duration_frames: z.number().int().min(1),
  contacts,
  hip: point,
  limb: limbSchema.nullable(),
  technique: techniqueSchema.nullable(),
  easing: easingSchema,
  camera,
  annotations: z.array(annotation),
  slow_motion: z.boolean(),
});

const body = z.strictObject({
  unit: z.enum(["cm", "px"]),
  height: z.number().positive(),
  shoulder_width: z.number().positive(),
  hip_width: z.number().positive(),
  torso: z.number().positive(),
  upper_arm: z.number().positive(),
  forearm: z.number().positive(),
  thigh: z.number().positive(),
  shin: z.number().positive(),
  head_radius: z.number().positive(),
});

export const MotionSpecSchema = z.strictObject({
  version: z.literal("1"),
  beta_id: z.string(),
  meta: z.strictObject({
    fps: z.number().int().min(12).max(60),
    width: z.number().int().positive(),
    height: z.number().int().positive(),
    duration_frames: z.number().int().min(1),
  }),
  image: z.strictObject({
    uri: z.string(),
    width: z.number().int().positive(),
    height: z.number().int().positive(),
  }),
  px_per_cm: z.number().positive(),
  body,
  holds: z.array(
    z.strictObject({
      id: holdId,
      center: point,
      radius: z.number().positive(),
      color: z.string(),
      role: z.enum(["start", "top", "route"]),
    }),
  ),
  keyframes: z.array(keyframe).min(1),
  chapters: z.array(
    z.strictObject({
      move_index: z.number().int().min(0),
      start_frame: z.number().int().min(0),
      title: z.string().min(1).max(48),
    }),
  ),
  provenance: z.strictObject({
    planner: z.string(),
    prompt: z.string().nullable(),
    model: z.string().nullable(),
    detector: z.string().nullable(),
  }),
});

export type MotionSpec = z.infer<typeof MotionSpecSchema>;
export type Keyframe = MotionSpec["keyframes"][number];
export type Annotation = Keyframe["annotations"][number];
export type Camera = Keyframe["camera"];
export type BodyModel = MotionSpec["body"];
export type SpecHold = MotionSpec["holds"][number];
export type Point = z.infer<typeof point>;
export type Limb = z.infer<typeof limbSchema>;
export type Easing = z.infer<typeof easingSchema>;

export const LIMBS: readonly Limb[] = ["lh", "rh", "lf", "rf"];

export function parseMotionSpec(raw: unknown): MotionSpec {
  const result = MotionSpecSchema.safeParse(raw);
  if (!result.success) {
    throw new Error(`Invalid MotionSpec:\n${z.prettifyError(result.error)}`);
  }
  return result.data;
}
