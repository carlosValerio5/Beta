"""Export ``contracts/openapi.json`` and deterministic example responses for BetaKit.

``python -m beta_api.openapi contracts/openapi.json`` (run by ``make contracts``). Examples come from
a real in-process run (synthetic wall, offline adapters, fixed clock and IDs) so they are always
shapes the API actually returns.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from beta_api.app import create_app
from beta_api.container import Container
from beta_api.settings import Settings
from beta_core.domain.geometry import BBox
from beta_core.domain.holds import Hold
from beta_core.domain.motion import MotionSpec
from beta_core.ports import MediaStore, RenderResult
from beta_core.testing import FixedClock, SequentialIds
from beta_vision.detect import match_holds
from beta_vision.synthetic import SyntheticWallGenerator

EXAMPLE_BASE_URL = "https://api.beta.example"


class _ExampleRenderer:
    def __init__(self, media: MediaStore) -> None:
        self.media = media

    def render(self, spec: MotionSpec, video_id: str) -> RenderResult:
        self.media.put(f"videos/{video_id}.mp4", b"example", "video/mp4")
        self.media.put(f"videos/{video_id}.jpg", b"example", "image/jpeg")
        return RenderResult(
            video_key=f"videos/{video_id}.mp4",
            poster_key=f"videos/{video_id}.jpg",
            duration_s=round(spec.meta.duration_frames / spec.meta.fps, 3),
        )


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _examples(tmp: Path) -> dict[str, Any]:
    settings = Settings(
        data_dir=tmp / "data",
        var_dir=tmp / "var",
        public_base_url=EXAMPLE_BASE_URL,
        renderer_url=None,
        anthropic_api_key=None,
        _env_file=None,
    )
    container = Container(settings, clock=FixedClock(), ids=SequentialIds())
    container.renderer = _ExampleRenderer(container.media)
    client = TestClient(create_app(container=container))

    wall = SyntheticWallGenerator(seed=7).generate()
    analysis = client.post(
        "/v1/analyses",
        files={"image": ("wall.jpg", wall.image, "image/jpeg")},
        data={"wall_height_cm": str(wall.height / wall.px_per_cm)},
        headers={"X-Device-Id": "dev_example"},
    ).json()
    detected = [
        Hold(id=h["id"], bbox=BBox(x=h["x"], y=h["y"], w=h["w"], h=h["h"]), color=h["color"])
        for h in analysis["holds"]
    ]
    mapping = {t.id: f.id for t, f in match_holds(wall.holds, detected, 15.0)}
    analysis = client.put(
        f"/v1/analyses/{analysis['id']}/problem",
        json={
            "start_hold_ids": [mapping[i] for i in wall.start_hold_ids],
            "top_hold_id": mapping[wall.top_hold_id],
            "color": wall.problem_color,
        },
    ).json()
    beta_id = client.post(
        f"/v1/analyses/{analysis['id']}/betas",
        json={
            "profile": {"height_cm": 172, "ape_index_cm": 3, "max_grade": "V4", "style": "balanced"}
        },
    ).json()["id"]
    beta = client.get(f"/v1/betas/{beta_id}").json()
    video_id = client.post(f"/v1/betas/{beta_id}/videos").json()["id"]
    video = client.get(f"/v1/videos/{video_id}").json()
    feedback = client.post(f"/v1/betas/{beta_id}/feedback", json={"kind": "sent"}).json()
    health = client.get("/health").json()
    return {
        "analysis": analysis,
        "beta": beta,
        "video": video,
        "feedback": feedback,
        "health": health,
    }


def export_contracts(root: Path) -> list[Path]:
    files = {"openapi.json": _dump(create_app(container=_bare_container()).openapi())}
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in _examples(Path(tmp)).items():
            files[f"api/examples/{name}.json"] = _dump(body)
    written = []
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def _bare_container() -> Container:
    tmp = Path(tempfile.mkdtemp(prefix="beta-openapi-"))
    return Container(
        Settings(data_dir=tmp / "data", var_dir=tmp / "var", anthropic_api_key=None, _env_file=None)
    )


def main(argv: list[str]) -> None:
    target = Path(argv[1]) if len(argv) > 1 else Path("contracts/openapi.json")
    for path in export_contracts(target.parent):
        print(path)


if __name__ == "__main__":
    main(sys.argv)
