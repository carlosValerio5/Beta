"""End-to-end HTTP flow: photo -> holds -> problem -> beta -> video -> feedback."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from beta_api.container import Container
from beta_api.settings import Settings
from beta_vision.synthetic import SyntheticWall


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["planner"] == "heuristic-planner@1"
    assert body["renderer"] is False


def test_upload_detects_holds_and_serves_image(
    client: TestClient, wall: SyntheticWall, upload_wall: Callable[..., Any]
) -> None:
    analysis = upload_wall(client, wall)
    assert len(analysis["holds"]) >= 25
    assert wall.problem_color in analysis["color_groups"]
    assert analysis["scale_method"] == "wall_height"
    assert analysis["image_url"].startswith("http://testserver/media/images/")
    image = client.get(analysis["image_url"].removeprefix("http://testserver"))
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/jpeg"


def test_upload_lands_in_bronze(
    client: TestClient, wall: SyntheticWall, settings: Settings, upload_wall: Callable[..., Any]
) -> None:
    upload_wall(client, wall)
    assert list((settings.data_dir / "bronze" / "images").rglob("*.jpg"))
    assert list((settings.data_dir / "bronze" / "events").rglob("events.jsonl"))


def test_upload_rejects_non_images(client: TestClient) -> None:
    response = client.post("/v1/analyses", files={"image": ("x.jpg", b"nope", "image/jpeg")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


def test_upload_size_limit(container: Container, wall: SyntheticWall) -> None:
    container.settings.max_upload_bytes = 1000
    from beta_api.app import create_app

    response = TestClient(create_app(container=container)).post(
        "/v1/analyses", files={"image": ("wall.jpg", wall.image, "image/jpeg")}
    )
    assert response.status_code == 413


def test_bad_device_id(client: TestClient, wall: SyntheticWall) -> None:
    response = client.post(
        "/v1/analyses",
        files={"image": ("wall.jpg", wall.image, "image/jpeg")},
        headers={"X-Device-Id": "not ok/../"},
    )
    assert response.status_code == 422


def test_unknown_analysis(client: TestClient) -> None:
    response = client.get("/v1/analyses/ana_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_select_problem(
    client: TestClient,
    wall: SyntheticWall,
    analysis: dict[str, Any],
    problem_selection: Callable[..., Any],
) -> None:
    selection = problem_selection(wall, analysis)
    put = client.put(f"/v1/analyses/{analysis['id']}/problem", json=selection)
    assert put.status_code == 200, put.text
    problem = client.get(f"/v1/analyses/{analysis['id']}").json()["problem"]
    assert problem["top_hold_id"] == selection["top_hold_id"]
    assert problem["color"] == wall.problem_color


def test_select_problem_rejects_unknown_hold(client: TestClient, analysis: dict[str, Any]) -> None:
    response = client.put(
        f"/v1/analyses/{analysis['id']}/problem",
        json={"start_hold_ids": [0], "top_hold_id": 999, "hold_ids": [1, 2]},
    )
    assert response.status_code == 422


def test_beta_requires_problem(client: TestClient, analysis: dict[str, Any]) -> None:
    response = client.post(f"/v1/analyses/{analysis['id']}/betas", json={"profile": {"height_cm": 175}})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state"


def test_beta_is_generated(ready_beta: dict[str, Any]) -> None:
    assert ready_beta["moves"]
    assert ready_beta["moves"][-1]["technique"] == "match"
    assert ready_beta["grade"].startswith("V")
    assert ready_beta["planner"] == "heuristic-planner@1"
    assert sum(m["is_crux"] for m in ready_beta["moves"]) == 1


def test_feedback(client: TestClient, ready_beta: dict[str, Any]) -> None:
    ok = client.post(f"/v1/betas/{ready_beta['id']}/feedback", json={"kind": "sent"})
    assert ok.status_code == 201
    bad = client.post(
        f"/v1/betas/{ready_beta['id']}/feedback", json={"kind": "move_looks_wrong", "move_index": 999}
    )
    assert bad.status_code == 422


def test_video_without_renderer_stops_at_directed(client: TestClient, ready_beta: dict[str, Any]) -> None:
    created = client.post(f"/v1/betas/{ready_beta['id']}/videos")
    assert created.status_code == 202
    video = client.get(f"/v1/videos/{created.json()['id']}").json()
    assert video["status"] == "directed"
    assert video["video_url"] is None
    assert len(video["chapters"]) == len(ready_beta["moves"])
    spec = client.get(f"/v1/videos/{video['id']}/spec").json()
    assert spec["version"] == "1"


def test_video_with_renderer(
    rendering_client: TestClient,
    wall: SyntheticWall,
    upload_wall: Callable[..., Any],
    problem_selection: Callable[..., Any],
) -> None:
    analysis = upload_wall(rendering_client, wall)
    rendering_client.put(f"/v1/analyses/{analysis['id']}/problem", json=problem_selection(wall, analysis))
    beta = rendering_client.post(
        f"/v1/analyses/{analysis['id']}/betas", json={"profile": {"height_cm": 170}}
    ).json()
    video_id = rendering_client.post(f"/v1/betas/{beta['id']}/videos").json()["id"]
    video = rendering_client.get(f"/v1/videos/{video_id}").json()
    assert video["status"] == "ready"
    assert video["duration_s"] > 0
    path = video["video_url"].removeprefix("http://testserver")
    ranged = rendering_client.get(path, headers={"Range": "bytes=0-7"})
    assert ranged.status_code == 206
    assert len(ranged.content) == 8


def test_video_needs_ready_beta(client: TestClient) -> None:
    assert client.post("/v1/betas/bet_missing/videos").status_code == 404
