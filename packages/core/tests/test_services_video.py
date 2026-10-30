from __future__ import annotations

import pytest

from beta_core.domain.events import EventName
from beta_core.domain.motion import MotionDraft, MotionSpec
from beta_core.domain.records import Analysis, BetaRecord, JobStatus, VideoRecord, VideoStatus
from beta_core.errors import AdapterError, InvalidStateError
from beta_core.ports import MotionRequest, RenderResult
from beta_core.services.generate_video import ProduceVideo, RequestVideo
from beta_core.testing import (
    DraftMotionDirector,
    FakeRenderer,
    FixedClock,
    InMemoryMediaStore,
    InMemoryRepository,
    RecordingEventSink,
    SequentialIds,
    ladder_analysis,
    ladder_beta_record,
)
from beta_core.validation import MotionSpecValidator


class BrokenDirector:
    name = "broken@1"

    def __init__(self) -> None:
        self.inner = DraftMotionDirector(MotionDraft(directions=[]))
        self.calls: list[MotionRequest] = []

    def direct(self, request: MotionRequest) -> MotionSpec:
        self.calls.append(request)
        spec = self.inner.direct(request)
        return spec.model_copy(update={"chapters": spec.chapters[:-1]})


class ExplodingRenderer:
    def render(self, spec: MotionSpec, video_id: str) -> RenderResult:
        raise AdapterError("renderer down")


@pytest.fixture
def env() -> dict:  # type: ignore[type-arg]
    media = InMemoryMediaStore()
    analyses = InMemoryRepository[Analysis]()
    analysis = ladder_analysis(media)
    analyses.save(analysis)
    betas = InMemoryRepository[BetaRecord]()
    beta = ladder_beta_record(analysis)
    betas.save(beta)
    return {
        "analyses": analyses,
        "betas": betas,
        "videos": InMemoryRepository[VideoRecord](),
        "media": media,
        "events": RecordingEventSink(),
        "ids": SequentialIds(),
        "clock": FixedClock(),
        "beta": beta,
    }


def request(env: dict) -> VideoRecord:  # type: ignore[type-arg]
    return RequestVideo(
        betas=env["betas"], videos=env["videos"], ids=env["ids"], clock=env["clock"]
    ).execute(env["beta"].id)


def produce(
    env: dict, director: object, renderer: object | None, record: VideoRecord
) -> VideoRecord:  # type: ignore[type-arg]
    return ProduceVideo(
        videos=env["videos"],
        betas=env["betas"],
        analyses=env["analyses"],
        media=env["media"],
        director=director,  # type: ignore[arg-type]
        validator=MotionSpecValidator(),
        renderer=renderer,  # type: ignore[arg-type]
        events=env["events"],
        clock=env["clock"],
    ).execute(record.id)


def test_request_requires_ready_beta(env: dict) -> None:  # type: ignore[type-arg]
    env["betas"].save(env["beta"].model_copy(update={"status": JobStatus.PENDING, "plan": None}))
    with pytest.raises(InvalidStateError):
        request(env)


def test_produce_with_renderer(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    assert record.status is VideoStatus.DIRECTING
    done = produce(env, DraftMotionDirector(MotionDraft(directions=[])), FakeRenderer(), record)
    assert done.status is VideoStatus.READY
    assert done.spec is not None
    assert done.video_key == f"videos/{record.id}.mp4"
    assert done.poster_key is not None
    assert env["events"].names() == [EventName.VIDEO_DIRECTED, EventName.VIDEO_RENDERED]


def test_produce_without_renderer_stops_at_directed(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    done = produce(env, DraftMotionDirector(MotionDraft(directions=[])), None, record)
    assert done.status is VideoStatus.DIRECTED
    assert done.video_key is None


def test_produce_fails_on_invalid_spec(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    director = BrokenDirector()
    done = produce(env, director, FakeRenderer(), record)
    assert done.status is VideoStatus.FAILED
    assert done.violations
    assert len(director.calls) == 2
    assert director.calls[1].previous_violations


def test_produce_renderer_error(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    done = produce(
        env, DraftMotionDirector(MotionDraft(directions=[])), ExplodingRenderer(), record
    )
    assert done.status is VideoStatus.FAILED
    assert done.spec is not None
    assert "renderer down" in (done.error or "")
    assert env["events"].names()[-1] == EventName.VIDEO_FAILED
