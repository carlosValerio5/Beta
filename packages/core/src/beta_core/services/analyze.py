from __future__ import annotations

from beta_core.domain.events import EventName
from beta_core.domain.records import Analysis, StoredImage
from beta_core.ports import (
    Clock,
    EventSink,
    HoldClassifier,
    HoldDetector,
    IdGenerator,
    ImagePreprocessor,
    MediaStore,
    RawImageSink,
    Repository,
)
from beta_core.scale import estimate_px_per_cm
from beta_core.services._events import emit


class AnalyzeBoulder:
    """Photo in → sanitized bronze copy, normalised image, detected holds, scale estimate."""

    def __init__(
        self,
        *,
        preprocessor: ImagePreprocessor,
        detector: HoldDetector,
        raw_sink: RawImageSink,
        media: MediaStore,
        analyses: Repository[Analysis],
        events: EventSink,
        ids: IdGenerator,
        clock: Clock,
        classifier: HoldClassifier | None = None,
    ) -> None:
        self._preprocessor = preprocessor
        self._detector = detector
        self._raw_sink = raw_sink
        self._media = media
        self._analyses = analyses
        self._events = events
        self._ids = ids
        self._clock = clock
        self._classifier = classifier

    def execute(
        self, raw: bytes, *, device_id: str, wall_height_cm: float | None = None
    ) -> Analysis:
        upload = self._preprocessor.sanitize(raw)
        raw_key = self._raw_sink.store_raw(upload)
        image = self._preprocessor.normalize(upload.data)
        image_key = f"images/{image.sha256}.jpg"
        self._media.put(image_key, image.data, image.content_type)

        holds = self._detector.detect(image)
        if self._classifier is not None:
            holds = self._classifier.classify(image, holds)
        scale = estimate_px_per_cm(holds, image.height, wall_height_cm)

        analysis = Analysis(
            id=self._ids.new("ana"),
            device_id=device_id,
            created_at=self._clock.now(),
            image=StoredImage(
                key=image_key,
                width=image.width,
                height=image.height,
                sha256=image.sha256,
                dhash=image.dhash,
            ),
            holds=tuple(holds),
            detector=self._detector.version,
            px_per_cm=scale.px_per_cm,
            scale_method=scale.method,
        )
        self._analyses.save(analysis)

        emit(
            self._events,
            self._clock,
            EventName.IMAGE_INGESTED,
            analysis.id,
            {
                "device_id": device_id,
                "raw_key": raw_key,
                "raw_sha256": upload.sha256,
                "content_type": upload.content_type,
                "gps_stripped": upload.gps_stripped,
                "image": analysis.image.model_dump(mode="json"),
                "wall_height_cm": wall_height_cm,
            },
        )
        emit(
            self._events,
            self._clock,
            EventName.HOLDS_DETECTED,
            analysis.id,
            {
                "detector": analysis.detector,
                "image_sha256": image.sha256,
                "holds": [h.model_dump(mode="json") for h in analysis.holds],
                "px_per_cm": scale.px_per_cm,
                "scale_method": scale.method.value,
                "scale_confidence": scale.confidence,
            },
        )
        return analysis
