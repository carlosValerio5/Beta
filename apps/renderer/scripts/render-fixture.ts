/**
 * Render a contract fixture to var/renders/ for eyeballing and frame checks.
 *   npm run render:fixture -w @beta/renderer -- [example-name] [background.jpg]
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderRouteVideo } from "../src/server/render";
import { parseMotionSpec } from "../src/spec";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const name = process.argv[2] ?? "ladder-directed";
const background = process.argv[3];

const spec = parseMotionSpec(
  JSON.parse(readFileSync(`${root}contracts/motion-spec/examples/${name}.json`, "utf-8")),
);
const image = background
  ? `data:image/jpeg;base64,${readFileSync(background).toString("base64")}`
  : null;

const started = Date.now();
const out = await renderRouteVideo(
  { video_id: name, spec, image_data_url: image },
  `${root}var/renders`,
);
console.log(`${out.videoPath} (${out.durationS.toFixed(1)} s) in ${Date.now() - started} ms`);
console.log(out.posterPath);
