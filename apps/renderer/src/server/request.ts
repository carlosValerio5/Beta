import { type MotionSpec, parseMotionSpec } from "../spec";

const VIDEO_ID = /^[A-Za-z0-9_-]{1,64}$/;
const IMAGE_DATA_URL = /^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/;

export type RenderRequest = {
  video_id: string;
  spec: MotionSpec;
  image_data_url: string | null;
};

export function parseRenderRequest(body: unknown): RenderRequest {
  if (typeof body !== "object" || body === null)
    throw new Error("request body must be a JSON object");
  const { video_id, spec, image_data_url } = body as Record<string, unknown>;
  if (typeof video_id !== "string" || !VIDEO_ID.test(video_id)) {
    throw new Error("video_id must be 1-64 characters of [A-Za-z0-9_-]");
  }
  if (image_data_url !== undefined && image_data_url !== null) {
    if (typeof image_data_url !== "string" || !IMAGE_DATA_URL.test(image_data_url)) {
      throw new Error("image_data_url must be a base64 data: URL of a JPEG, PNG or WebP image");
    }
  }
  return {
    video_id,
    spec: parseMotionSpec(spec),
    image_data_url: typeof image_data_url === "string" ? image_data_url : null,
  };
}

/** The still used as the poster: inside the crux (first slow-motion move), else mid-video. */
export function posterFrame(spec: MotionSpec): number {
  const crux = spec.keyframes.find((k) => k.slow_motion && k.move_index >= 0);
  const chosen = crux ?? spec.keyframes[Math.floor(spec.keyframes.length / 2)];
  if (!chosen) return 0;
  return chosen.start_frame + Math.floor(chosen.duration_frames * 0.6);
}
