import { describe, expect, it } from "vitest";
import { parseRenderRequest, posterFrame } from "../src/server/request";
import { parseMotionSpec } from "../src/spec";
import { readContract } from "./fixtures";

const spec = readContract("motion-spec/examples/ladder-directed.json");

describe("parseRenderRequest", () => {
  it("accepts a spec with an inline image", () => {
    const req = parseRenderRequest({
      video_id: "vid_1",
      spec,
      image_data_url: "data:image/jpeg;base64,AAAA",
    });
    expect(req.video_id).toBe("vid_1");
    expect(req.spec.beta_id).toBe("bet_ladder");
  });

  it("allows a missing image (synthetic wall backdrop)", () => {
    expect(parseRenderRequest({ video_id: "vid_1", spec }).image_data_url).toBeNull();
  });

  it.each([
    [{ spec }, /video_id/],
    [{ video_id: "../etc/passwd", spec }, /video_id/],
    [{ video_id: "vid_1", spec, image_data_url: "http://evil.example/x.jpg" }, /image/],
  ])("rejects %#", (body, message) => {
    expect(() => parseRenderRequest(body)).toThrow(message);
  });
});

describe("posterFrame", () => {
  it("lands inside the crux segment", () => {
    const parsed = parseMotionSpec(spec);
    const frame = posterFrame(parsed);
    const crux = parsed.keyframes.find((k) => k.slow_motion && k.move_index >= 0);
    if (!crux) throw new Error("fixture has no crux");
    expect(frame).toBeGreaterThanOrEqual(crux.start_frame);
    expect(frame).toBeLessThan(crux.start_frame + crux.duration_frames);
  });
});
