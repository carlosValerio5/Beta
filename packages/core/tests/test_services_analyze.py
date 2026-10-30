import pytest

from beta_core.domain.events import EventName
from beta_core.domain.records import Analysis
from beta_core.errors import InvalidStateError, NotFoundError, UnknownHoldError
from beta_core.scale import ScaleMethod
from beta_core.services.analyze import AnalyzeBoulder
from beta_core.services.select_problem import SelectProblem
from beta_core.testing import (
    FakeDetector,
    FakePreprocessor,
    FixedClock,
    InMemoryMediaStore,
    InMemoryRawImageSink,
    InMemoryRepository,
    RecordingEventSink,
    SequentialIds,
    ladder_problem,
)


@pytest.fixture
def deps() -> dict:  # type: ignore[type-arg]
    return {
        "preprocessor": FakePreprocessor(gps=True),
        "detector": FakeDetector(list(ladder_problem().holds)),
        "raw_sink": InMemoryRawImageSink(),
        "media": InMemoryMediaStore(),
        "analyses": InMemoryRepository[Analysis](),
        "events": RecordingEventSink(),
        "ids": SequentialIds(),
        "clock": FixedClock(),
    }


def analyze(deps: dict) -> Analysis:  # type: ignore[type-arg]
    return AnalyzeBoulder(**deps).execute(b"raw-bytes", device_id="dev_1")


def test_analyze_persists_and_emits(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = analyze(deps)
    assert deps["analyses"].get(analysis.id) == analysis
    assert analysis.device_id == "dev_1"
    assert len(analysis.holds) == len(ladder_problem().holds)
    assert deps["media"].exists(analysis.image.key)
    assert deps["raw_sink"].stored
    names = [e.name for e in deps["events"].events]
    assert names == [EventName.IMAGE_INGESTED, EventName.HOLDS_DETECTED]
    assert deps["events"].events[0].payload["gps_stripped"] is True


def test_analyze_estimates_scale_from_wall_height(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = AnalyzeBoulder(**deps).execute(b"raw", device_id="d", wall_height_cm=500)
    assert analysis.scale_method is ScaleMethod.WALL_HEIGHT
    assert analysis.px_per_cm == pytest.approx(analysis.image.height / 500)


def test_analyze_color_groups(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = analyze(deps)
    groups = analysis.color_groups()
    assert set(groups) == {h.color for h in analysis.holds}


def test_select_problem_by_color(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = analyze(deps)
    select = SelectProblem(analyses=deps["analyses"], events=deps["events"], clock=deps["clock"])
    updated = select.execute(analysis.id, start_hold_ids=[0, 1], top_hold_id=8, color="yellow")
    assert updated.problem is not None
    assert {h.color for h in updated.problem.holds} == {"yellow"}
    assert deps["events"].events[-1].name == EventName.PROBLEM_SELECTED


def test_select_problem_by_ids_includes_start_and_top(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = analyze(deps)
    select = SelectProblem(analyses=deps["analyses"], events=deps["events"], clock=deps["clock"])
    updated = select.execute(analysis.id, start_hold_ids=[0], top_hold_id=8, hold_ids=[4, 5])
    assert updated.problem is not None
    assert updated.problem.hold_ids == frozenset({0, 4, 5, 8})


def test_select_problem_unknown_hold(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = analyze(deps)
    select = SelectProblem(analyses=deps["analyses"], events=deps["events"], clock=deps["clock"])
    with pytest.raises(UnknownHoldError):
        select.execute(analysis.id, start_hold_ids=[0], top_hold_id=77, hold_ids=[4])


def test_select_problem_requires_hold_ids_or_color(deps: dict) -> None:  # type: ignore[type-arg]
    analysis = analyze(deps)
    select = SelectProblem(analyses=deps["analyses"], events=deps["events"], clock=deps["clock"])
    with pytest.raises(InvalidStateError):
        select.execute(analysis.id, start_hold_ids=[0], top_hold_id=8)


def test_select_problem_missing_analysis(deps: dict) -> None:  # type: ignore[type-arg]
    select = SelectProblem(analyses=deps["analyses"], events=deps["events"], clock=deps["clock"])
    with pytest.raises(NotFoundError):
        select.execute("ana_missing", start_hold_ids=[0], top_hold_id=8, color="yellow")
