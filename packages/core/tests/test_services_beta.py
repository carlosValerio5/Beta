from __future__ import annotations

import pytest

from beta_core.domain.beta import BetaPlan
from beta_core.domain.events import EventName
from beta_core.domain.records import Analysis, BetaRecord, JobStatus
from beta_core.errors import AdapterError, InvalidStateError
from beta_core.ports import BetaRequest
from beta_core.services.generate_beta import ProduceBeta, RequestBeta
from beta_core.testing import (
    FakeMarkRenderer,
    FixedClock,
    InMemoryMediaStore,
    InMemoryRepository,
    RecordingEventSink,
    SequentialIds,
    ladder_analysis,
    ladder_plan,
    profile_175,
)
from beta_core.validation import BetaValidator


class ScriptedPlanner:
    """Returns the queued plans in order; raises queued exceptions."""

    name = "scripted@1"

    def __init__(self, *outputs: BetaPlan | Exception) -> None:
        self.outputs = list(outputs)
        self.requests: list[BetaRequest] = []

    def plan(self, request: BetaRequest) -> BetaPlan:
        self.requests.append(request)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def broken_plan() -> BetaPlan:
    plan = ladder_plan()
    return plan.model_copy(update={"moves": plan.moves[:-1]})  # never matches the top


@pytest.fixture
def env() -> dict:  # type: ignore[type-arg]
    analyses = InMemoryRepository[Analysis]()
    media = InMemoryMediaStore()
    analysis = ladder_analysis(media)
    analyses.save(analysis)
    return {
        "analyses": analyses,
        "betas": InMemoryRepository[BetaRecord](),
        "media": media,
        "events": RecordingEventSink(),
        "ids": SequentialIds(),
        "clock": FixedClock(),
        "analysis": analysis,
    }


def request(env: dict) -> BetaRecord:  # type: ignore[type-arg]
    return RequestBeta(
        analyses=env["analyses"], betas=env["betas"], ids=env["ids"], clock=env["clock"]
    ).execute(env["analysis"].id, profile_175())


def produce(env: dict, planner: ScriptedPlanner, record: BetaRecord) -> BetaRecord:  # type: ignore[type-arg]
    return ProduceBeta(
        analyses=env["analyses"],
        betas=env["betas"],
        media=env["media"],
        marks=FakeMarkRenderer(),
        planner=planner,
        validator=BetaValidator(),
        events=env["events"],
        clock=env["clock"],
    ).execute(record.id)


def test_request_creates_pending(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    assert record.status is JobStatus.PENDING
    assert env["betas"].get(record.id) == record


def test_request_requires_selected_problem(env: dict) -> None:  # type: ignore[type-arg]
    no_problem = env["analysis"].model_copy(update={"problem": None})
    env["analyses"].save(no_problem)
    with pytest.raises(InvalidStateError):
        request(env)


def test_produce_success_first_try(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    planner = ScriptedPlanner(ladder_plan())
    done = produce(env, planner, record)
    assert done.status is JobStatus.READY
    assert done.attempts == 1
    assert done.plan is not None
    assert done.plan.id == record.id
    assert done.plan.analysis_id == env["analysis"].id
    assert env["events"].names() == [EventName.BETA_GENERATED]
    assert planner.requests[0].image.data.startswith(b"marked:")


def test_produce_repairs_with_feedback(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    planner = ScriptedPlanner(broken_plan(), ladder_plan())
    done = produce(env, planner, record)
    assert done.status is JobStatus.READY
    assert done.attempts == 2
    assert planner.requests[1].previous_violations
    assert planner.requests[1].previous_attempt is not None


def test_produce_fails_after_max_repairs(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    planner = ScriptedPlanner(broken_plan(), broken_plan(), broken_plan())
    done = produce(env, planner, record)
    assert done.status is JobStatus.FAILED
    assert done.attempts == 3
    assert done.violations
    assert env["events"].names() == [EventName.BETA_FAILED]


def test_produce_adapter_error(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    done = produce(env, ScriptedPlanner(AdapterError("anthropic timeout")), record)
    assert done.status is JobStatus.FAILED
    assert done.error is not None
    assert "anthropic timeout" in done.error


def test_produce_is_idempotent_for_finished_records(env: dict) -> None:  # type: ignore[type-arg]
    record = request(env)
    done = produce(env, ScriptedPlanner(ladder_plan()), record)
    again = produce(env, ScriptedPlanner(), done)
    assert again == done
