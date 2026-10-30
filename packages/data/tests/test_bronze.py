from __future__ import annotations

from datetime import UTC, datetime

from beta_core.domain.events import DomainEvent, EventName
from beta_core.ports import SanitizedUpload
from beta_data.bronze import BronzeWriter, read_events
from beta_data.layout import Lakehouse


def upload(data: bytes = b"\xff\xd8jpeg-bytes") -> SanitizedUpload:
    import hashlib

    return SanitizedUpload(
        data=data, sha256=hashlib.sha256(data).hexdigest(), content_type="image/jpeg", gps_stripped=False
    )


def event(name: EventName, day: int, entity: str = "ana_1") -> DomainEvent:
    return DomainEvent(
        name=name,
        occurred_at=datetime(2026, 10, day, 12, 0, tzinfo=UTC),
        entity_id=entity,
        payload={"n": day},
    )


def test_raw_images_are_content_addressed(lake: Lakehouse) -> None:
    writer = BronzeWriter(lake)
    up = upload()
    key = writer.store_raw(up)
    assert key == f"bronze/images/{up.sha256[:2]}/{up.sha256}.jpg"
    path = lake.root / key
    assert path.read_bytes() == up.data
    mtime = path.stat().st_mtime_ns
    assert writer.store_raw(up) == key
    assert path.stat().st_mtime_ns == mtime  # never rewritten


def test_events_append_to_date_partitions(lake: Lakehouse) -> None:
    writer = BronzeWriter(lake)
    writer.emit(event(EventName.IMAGE_INGESTED, 29))
    writer.emit(event(EventName.HOLDS_DETECTED, 30))
    writer.emit(event(EventName.PROBLEM_SELECTED, 30))
    assert (lake.bronze / "events" / "date=2026-10-29" / "events.jsonl").is_file()
    day30 = (lake.bronze / "events" / "date=2026-10-30" / "events.jsonl").read_text().splitlines()
    assert len(day30) == 2


def test_read_events_roundtrip_in_order(lake: Lakehouse) -> None:
    writer = BronzeWriter(lake)
    sent = [event(EventName.IMAGE_INGESTED, 29), event(EventName.HOLDS_DETECTED, 30)]
    for e in sent:
        writer.emit(e)
    assert list(read_events(lake)) == sent


def test_ground_truth_is_written_once(lake: Lakehouse) -> None:
    writer = BronzeWriter(lake)
    path = writer.store_ground_truth("abc", {"holds": []})
    assert path.is_file()
    assert writer.store_ground_truth("abc", {"holds": [1]}) == path
    assert '"holds": []' in path.read_text()
