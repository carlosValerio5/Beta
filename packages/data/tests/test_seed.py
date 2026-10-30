from __future__ import annotations

from collections import Counter

from beta_core.domain.events import EventName
from beta_data.bronze import read_events
from beta_data.layout import Lakehouse


def test_seed_populates_bronze(seeded: Lakehouse) -> None:
    images = list((seeded.bronze / "images").rglob("*.jpg"))
    truths = list((seeded.bronze / "ground_truth").glob("*.json"))
    assert len(images) == 3
    assert len(truths) == 3


def test_seed_runs_the_whole_pipeline(seeded: Lakehouse) -> None:
    names = Counter(e.name for e in read_events(seeded))
    for expected in (
        EventName.IMAGE_INGESTED,
        EventName.HOLDS_DETECTED,
        EventName.PROBLEM_SELECTED,
        EventName.BETA_GENERATED,
        EventName.VIDEO_DIRECTED,
    ):
        assert names[expected] == 3, expected
    assert names[EventName.FEEDBACK_RECORDED] + names[EventName.PLAYBACK_RECORDED] >= 3


def test_seed_is_deterministic(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from beta_data.seed import seed

    a, b = Lakehouse(tmp_path / "a"), Lakehouse(tmp_path / "b")
    seed(a, count=1)
    seed(b, count=1)
    images_a = sorted(p.name for p in (a.bronze / "images").rglob("*.jpg"))
    images_b = sorted(p.name for p in (b.bronze / "images").rglob("*.jpg"))
    assert images_a == images_b
