import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import { posterFrame, type RenderRequest } from "./request";

const ENTRY = fileURLToPath(new URL("../index.ts", import.meta.url));
let serveUrl: Promise<string> | null = null;

/** Bundle the Remotion project once per process. */
export function getServeUrl(): Promise<string> {
  serveUrl ??= bundle({ entryPoint: ENTRY });
  return serveUrl;
}

export type RenderOutput = { videoPath: string; posterPath: string; durationS: number };

export async function renderRouteVideo(req: RenderRequest, outDir: string): Promise<RenderOutput> {
  await mkdir(outDir, { recursive: true });
  const inputProps = { spec: req.spec, imageSrc: req.image_data_url };
  const url = await getServeUrl();
  const composition = await selectComposition({ serveUrl: url, id: "RouteVideo", inputProps });
  const videoPath = join(outDir, `${req.video_id}.mp4`);
  const posterPath = join(outDir, `${req.video_id}.jpg`);
  await renderMedia({
    composition,
    serveUrl: url,
    codec: "h264",
    crf: 22,
    outputLocation: videoPath,
    inputProps,
  });
  await renderStill({
    composition,
    serveUrl: url,
    output: posterPath,
    inputProps,
    frame: posterFrame(req.spec),
    imageFormat: "jpeg",
  });
  return { videoPath, posterPath, durationS: req.spec.meta.duration_frames / req.spec.meta.fps };
}
