"""End-to-end smoke test against a running API (+ renderer): photo → holds → beta → MP4.

    make dev            # in one terminal (API :8000 + renderer :8787)
    make smoke          # in another

Uses a synthetic wall so it needs no real photos; writes results to var/e2e/smoke/.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

from beta_core.domain.geometry import BBox
from beta_core.domain.holds import Hold
from beta_vision.detect import match_holds
from beta_vision.synthetic import SyntheticWallGenerator

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path("var/e2e/smoke")


def wait_for(client: httpx.Client, url: str, timeout_s: float = 90) -> dict:  # type: ignore[type-arg]
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            response = client.get(url)
            if response.status_code == 200:
                return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPError:
            pass
        if time.monotonic() > deadline:
            raise SystemExit(f"timed out waiting for {url}")
        time.sleep(1)


def poll(client: httpx.Client, url: str, done: set[str], timeout_s: float) -> dict:  # type: ignore[type-arg]
    deadline = time.monotonic() + timeout_s
    while True:
        body: dict = client.get(url).json()  # type: ignore[type-arg]
        if body["status"] in done:
            return body
        if time.monotonic() > deadline:
            raise SystemExit(f"timed out polling {url}: {body['status']}")
        time.sleep(1)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(base_url=API, timeout=60, headers={"X-Device-Id": "dev_smoke"})
    health = wait_for(client, "/health")
    print("health:", health)

    wall = SyntheticWallGenerator(seed=42).generate()
    started = time.monotonic()
    analysis = client.post(
        "/v1/analyses",
        files={"image": ("wall.jpg", wall.image, "image/jpeg")},
        data={"wall_height_cm": str(wall.height / wall.px_per_cm)},
    ).json()
    print(
        f"analysis {analysis['id']}: {len(analysis['holds'])} holds, colours {list(analysis['color_groups'])}"
    )

    detected = [
        Hold(id=h["id"], bbox=BBox(x=h["x"], y=h["y"], w=h["w"], h=h["h"]), color=h["color"])
        for h in analysis["holds"]
    ]
    mapping = {t.id: f.id for t, f in match_holds(wall.holds, detected, 15.0)}
    client.put(
        f"/v1/analyses/{analysis['id']}/problem",
        json={
            "start_hold_ids": [mapping[i] for i in wall.start_hold_ids],
            "top_hold_id": mapping[wall.top_hold_id],
            "color": wall.problem_color,
        },
    ).raise_for_status()

    beta_id = client.post(
        f"/v1/analyses/{analysis['id']}/betas",
        json={
            "profile": {"height_cm": 172, "ape_index_cm": 2, "max_grade": "V4", "style": "balanced"}
        },
    ).json()["id"]
    beta = poll(client, f"/v1/betas/{beta_id}", {"ready", "failed"}, timeout_s=180)
    beta_s = time.monotonic() - started
    print(
        f"beta {beta['status']} in {beta_s:.1f}s: {len(beta['moves'])} moves, {beta['grade']} via {beta['planner']}"
    )
    if beta["status"] != "ready":
        raise SystemExit(f"beta failed: {beta['error']} {beta['violations']}")

    video_id = client.post(f"/v1/betas/{beta_id}/videos").json()["id"]
    video = poll(client, f"/v1/videos/{video_id}", {"ready", "directed", "failed"}, timeout_s=900)
    total_s = time.monotonic() - started
    print(f"video {video['status']} after {total_s:.1f}s total, {len(video['chapters'])} chapters")

    summary = {
        "api": API,
        "health": health,
        "analysis_id": analysis["id"],
        "beta_id": beta_id,
        "video_id": video_id,
        "n_holds": len(analysis["holds"]),
        "n_moves": len(beta["moves"]),
        "grade": beta["grade"],
        "planner": beta["planner"],
        "video_status": video["status"],
        "beta_seconds": round(beta_s, 2),
        "total_seconds": round(total_s, 2),
    }
    if video["status"] == "ready":
        for name, url in (("route.mp4", video["video_url"]), ("poster.jpg", video["poster_url"])):
            path = url.split("/media/", 1)[1]
            (OUT / name).write_bytes(client.get(f"/media/{path}").content)
        summary["video_bytes"] = (OUT / "route.mp4").stat().st_size
        summary["duration_s"] = video["duration_s"]
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if video["status"] != "ready":
        raise SystemExit(f"video not rendered: {video['status']} {video['error']}")


if __name__ == "__main__":
    main()
