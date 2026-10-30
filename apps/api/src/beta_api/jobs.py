"""Background jobs (ADR-0008). A crash must never leave a record stuck in a pending state."""

from __future__ import annotations

import logging

from beta_api.container import Container
from beta_core.domain.records import JobStatus, VideoStatus

log = logging.getLogger("beta_api.jobs")


def run_beta(container: Container, beta_id: str) -> None:
    try:
        container.produce_beta().execute(beta_id)
    except Exception:
        log.exception("beta job %s crashed", beta_id)
        record = container.betas.get(beta_id)
        if record.status is JobStatus.PENDING:
            container.betas.save(
                record.model_copy(
                    update={
                        "status": JobStatus.FAILED,
                        "error": "internal error",
                        "updated_at": container.clock.now(),
                    }
                )
            )


def run_video(container: Container, video_id: str) -> None:
    try:
        container.produce_video().execute(video_id)
    except Exception:
        log.exception("video job %s crashed", video_id)
        record = container.videos.get(video_id)
        if not record.status.is_terminal:
            container.videos.save(
                record.model_copy(
                    update={
                        "status": VideoStatus.FAILED,
                        "error": "internal error",
                        "updated_at": container.clock.now(),
                    }
                )
            )
