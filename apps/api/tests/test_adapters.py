from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
import pytest

from beta_api.container import Container
from beta_api.media import LocalMediaStore
from beta_api.renderer import RemotionHttpRenderer
from beta_api.repositories import Database, SqliteRepository
from beta_api.settings import Settings
from beta_core.contracts import ladder_motion_spec
from beta_core.domain.records import Analysis
from beta_core.errors import AdapterError, InvalidInputError, NotFoundError
from beta_core.testing import InMemoryMediaStore, ladder_analysis
from beta_llm.planner import ClaudeBetaPlanner


def test_sqlite_repository_roundtrip(tmp_path: Path) -> None:
    db = Database(tmp_path / "beta.sqlite3")
    repo = SqliteRepository(db, "analyses", Analysis)
    analysis = ladder_analysis(InMemoryMediaStore())
    repo.save(analysis)
    assert repo.get(analysis.id) == analysis
    assert repo.find(device_id="dev_test") == [analysis]
    assert repo.find(device_id="other") == []
    again = SqliteRepository(Database(tmp_path / "beta.sqlite3"), "analyses", Analysis)
    assert again.get(analysis.id) == analysis


def test_sqlite_repository_not_found(tmp_path: Path) -> None:
    repo = SqliteRepository(Database(tmp_path / "db.sqlite3"), "analyses", Analysis)
    with pytest.raises(NotFoundError):
        repo.get("nope")


def test_media_store(tmp_path: Path) -> None:
    media = LocalMediaStore(tmp_path)
    media.put("images/a.jpg", b"abc", "image/jpeg")
    assert media.get("images/a.jpg") == b"abc"
    assert media.exists("images/a.jpg")
    assert media.path("images/a.jpg") == tmp_path / "images" / "a.jpg"


@pytest.mark.parametrize("key", ["../etc/passwd", "/abs/path", "images/../../x", ""])
def test_media_store_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    with pytest.raises(InvalidInputError):
        LocalMediaStore(tmp_path).put(key, b"x", "image/jpeg")


def test_remotion_renderer_posts_spec_and_stores_files(tmp_path: Path) -> None:
    media = LocalMediaStore(tmp_path)
    spec = ladder_motion_spec()
    media.put(spec.image.uri, b"\xff\xd8photo", "image/jpeg")
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "video_base64": base64.b64encode(b"MP4DATA").decode(),
                "poster_base64": base64.b64encode(b"JPGDATA").decode(),
                "duration_s": 18.4,
            },
        )

    renderer = RemotionHttpRenderer(
        "http://renderer", media, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    result = renderer.render(spec, "vid_1")

    assert seen["video_id"] == "vid_1"
    assert str(seen["image_data_url"]).startswith("data:image/jpeg;base64,")
    assert media.get(result.video_key) == b"MP4DATA"
    assert media.get(result.poster_key) == b"JPGDATA"
    assert result.duration_s == pytest.approx(18.4)


@pytest.mark.parametrize("status", [400, 500])
def test_remotion_renderer_errors(tmp_path: Path, status: int) -> None:
    media = LocalMediaStore(tmp_path)
    spec = ladder_motion_spec()
    media.put(spec.image.uri, b"\xff\xd8", "image/jpeg")
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status, json={"error": "x"})))
    with pytest.raises(AdapterError, match=str(status)):
        RemotionHttpRenderer("http://renderer", media, client=client).render(spec, "vid_1")


def test_container_uses_claude_when_key_present(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        var_dir=tmp_path / "var",
        anthropic_api_key="sk-ant-test",
        _env_file=None,  # type: ignore[call-arg]
    )
    container = Container(settings)
    assert container.planner.name == ClaudeBetaPlanner.name
    assert container.describe()["planner"] == ClaudeBetaPlanner.name
