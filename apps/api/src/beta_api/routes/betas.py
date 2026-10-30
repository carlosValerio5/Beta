from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from beta_api import jobs
from beta_api.container import Container
from beta_api.routes import get_container
from beta_api.schemas import BetaIn, BetaOut, FeedbackIn, FeedbackOut, VideoOut, video_out

router = APIRouter(prefix="/v1", tags=["betas"])
ContainerDep = Annotated[Container, Depends(get_container)]


@router.post(
    "/analyses/{analysis_id}/betas",
    status_code=202,
    response_model=BetaOut,
    summary="Request a beta (generated in the background; poll GET /v1/betas/{id})",
)
def request_beta(
    analysis_id: str, body: BetaIn, background: BackgroundTasks, container: ContainerDep
) -> BetaOut:
    record = container.request_beta().execute(analysis_id, body.profile.to_domain())
    background.add_task(jobs.run_beta, container, record.id)
    return BetaOut.of(record)


@router.get("/betas/{beta_id}", response_model=BetaOut, summary="Get a beta")
def get_beta(beta_id: str, container: ContainerDep) -> BetaOut:
    return BetaOut.of(container.betas.get(beta_id))


@router.post(
    "/betas/{beta_id}/feedback",
    status_code=201,
    response_model=FeedbackOut,
    summary="Send feedback",
)
def send_feedback(beta_id: str, body: FeedbackIn, container: ContainerDep) -> FeedbackOut:
    feedback = container.record_feedback().execute(beta_id, body.kind, body.move_index, body.note)
    return FeedbackOut.of(feedback)


@router.post(
    "/betas/{beta_id}/videos",
    status_code=202,
    response_model=VideoOut,
    summary="Request a route video (directed + rendered in the background)",
)
def request_video(beta_id: str, background: BackgroundTasks, container: ContainerDep) -> VideoOut:
    record = container.request_video().execute(beta_id)
    background.add_task(jobs.run_video, container, record.id)
    return video_out(record, None, None)
