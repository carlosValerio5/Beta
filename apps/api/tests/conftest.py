from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from beta_api.app import create_app
from beta_api.container import Container
from beta_api.settings import Settings
from beta_core.domain.motion import MotionSpec
from beta_core.ports import MediaStore, RenderResult
from beta_core.testing import FixedClock, SequentialIds
from beta_vision.detect import match_holds
from beta_vision.synthetic import SyntheticWall, SyntheticWallGenerator


class StubRenderer:
    """Writes placeholder media instead of running Remotion."""

    def __init__(self, media: MediaStore) -> None:
        self.media = media

    def render(self, spec: MotionSpec, video_id: str) -> RenderResult:
        self.media.put(f"videos/{video_id}.mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 64, "video/mp4")
        self.media.put(f"videos/{video_id}.jpg", b"\xff\xd8poster", "image/jpeg")
        return RenderResult(
            video_key=f"videos/{video_id}.mp4",
            poster_key=f"videos/{video_id}.jpg",
            duration_s=spec.meta.duration_frames / spec.meta.fps,
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        var_dir=tmp_path / "var",
        public_base_url="http://testserver",
        renderer_url=None,
        anthropic_api_key=None,
        _env_file=None,  # type: ignore[call-arg]
    )


@pytest.fixture
def container(settings: Settings) -> Container:
    return Container(settings, clock=FixedClock(), ids=SequentialIds())


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container=container))


@pytest.fixture
def rendering_client(container: Container) -> TestClient:
    container.renderer = StubRenderer(container.media)
    return TestClient(create_app(container=container))


@pytest.fixture(scope="session")
def wall() -> SyntheticWall:
    return SyntheticWallGenerator(seed=11).generate()


def upload_wall(client: TestClient, wall: SyntheticWall) -> dict[str, Any]:
    response = client.post(
        "/v1/analyses",
        files={"image": ("wall.jpg", wall.image, "image/jpeg")},
        data={"wall_height_cm": str(wall.height / wall.px_per_cm)},
        headers={"X-Device-Id": "dev_test"},
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def problem_selection(wall: SyntheticWall, analysis: dict[str, Any]) -> dict[str, Any]:
    from beta_core.domain.geometry import BBox
    from beta_core.domain.holds import Hold

    detected = [
        Hold(id=h["id"], bbox=BBox(x=h["x"], y=h["y"], w=h["w"], h=h["h"]), color=h["color"])
        for h in analysis["holds"]
    ]
    mapping = {t.id: f.id for t, f in match_holds(wall.holds, detected, 15.0)}
    return {
        "start_hold_ids": [mapping[i] for i in wall.start_hold_ids],
        "top_hold_id": mapping[wall.top_hold_id],
        "color": wall.problem_color,
    }


@pytest.fixture
def analysis(client: TestClient, wall: SyntheticWall) -> dict[str, Any]:
    return upload_wall(client, wall)


@pytest.fixture
def ready_beta(client: TestClient, wall: SyntheticWall, analysis: dict[str, Any]) -> dict[str, Any]:
    put = client.put(f"/v1/analyses/{analysis['id']}/problem", json=problem_selection(wall, analysis))
    assert put.status_code == 200, put.text
    created = client.post(
        f"/v1/analyses/{analysis['id']}/betas", json={"profile": {"height_cm": 175, "style": "balanced"}}
    )
    assert created.status_code == 202, created.text
    beta: dict[str, Any] = client.get(f"/v1/betas/{created.json()['id']}").json()
    assert beta["status"] == "ready", beta
    return beta


@pytest.fixture(name="upload_wall")
def _upload_wall() -> Any:
    return upload_wall


@pytest.fixture(name="problem_selection")
def _problem_selection() -> Any:
    return problem_selection
