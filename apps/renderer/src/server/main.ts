/**
 * Render service (ADR-0011). Internal only — bind to localhost or a private network.
 *   GET  /health  -> {"ok": true}
 *   POST /render  {video_id, spec, image_data_url?} -> {video_base64, poster_base64, duration_s}
 */
import { mkdtemp, readFile, rm } from "node:fs/promises";
import http from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { renderRouteVideo } from "./render";
import { parseRenderRequest } from "./request";

const PORT = Number(process.env.RENDERER_PORT ?? 8787);
const HOST = process.env.RENDERER_HOST ?? "127.0.0.1";
const MAX_BODY_BYTES = 25 * 1024 * 1024;

let queue: Promise<unknown> = Promise.resolve();
function serialised<T>(task: () => Promise<T>): Promise<T> {
  const next = queue.then(task, task);
  queue = next.catch(() => undefined);
  return next;
}

function send(res: http.ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readJson(req: http.IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new Error("request body too large");
    chunks.push(chunk as Buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf-8"));
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") return send(res, 200, { ok: true });
  if (req.method !== "POST" || req.url !== "/render") return send(res, 404, { error: "not found" });

  let request: ReturnType<typeof parseRenderRequest>;
  try {
    request = parseRenderRequest(await readJson(req));
  } catch (err) {
    return send(res, 400, { error: (err as Error).message });
  }

  const started = Date.now();
  const dir = await mkdtemp(join(tmpdir(), "beta-render-"));
  try {
    const out = await serialised(() => renderRouteVideo(request, dir));
    const [video, poster] = await Promise.all([readFile(out.videoPath), readFile(out.posterPath)]);
    console.log(
      `rendered ${request.video_id} in ${Date.now() - started} ms (${video.length} bytes)`,
    );
    send(res, 200, {
      video_base64: video.toString("base64"),
      poster_base64: poster.toString("base64"),
      duration_s: out.durationS,
    });
  } catch (err) {
    console.error(`render ${request.video_id} failed`, err);
    send(res, 500, { error: "render failed" });
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

server.listen(PORT, HOST, () => console.log(`renderer listening on http://${HOST}:${PORT}`));
