from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from beta_api.container import Container
from beta_api.routes import get_container
from beta_api.schemas import AnalysisOut, ProblemIn, analysis_out

router = APIRouter(prefix="/v1", tags=["analyses"])

DEVICE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
ContainerDep = Annotated[Container, Depends(get_container)]


@router.post(
    "/analyses", status_code=201, response_model=AnalysisOut, summary="Upload a wall photo"
)
async def create_analysis(
    container: ContainerDep,
    image: Annotated[UploadFile, File(description="JPEG, PNG or WebP photo of the boulder")],
    wall_height_cm: Annotated[float | None, Form(gt=50, lt=2000)] = None,
    device_id: Annotated[str, Header(alias="X-Device-Id", pattern=DEVICE_ID_PATTERN)] = "anonymous",
) -> AnalysisOut:
    limit = container.settings.max_upload_bytes
    data = await image.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"image larger than {limit} bytes")
    analysis = await run_in_threadpool(
        container.analyze().execute, data, device_id=device_id, wall_height_cm=wall_height_cm
    )
    return analysis_out(analysis, container.media_url(analysis.image.key) or "")


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut, summary="Get an analysis")
def get_analysis(analysis_id: str, container: ContainerDep) -> AnalysisOut:
    analysis = container.analyses.get(analysis_id)
    return analysis_out(analysis, container.media_url(analysis.image.key) or "")


@router.put(
    "/analyses/{analysis_id}/problem",
    response_model=AnalysisOut,
    summary="Choose the problem's holds",
)
def select_problem(analysis_id: str, body: ProblemIn, container: ContainerDep) -> AnalysisOut:
    analysis = container.select_problem().execute(
        analysis_id,
        start_hold_ids=body.start_hold_ids,
        top_hold_id=body.top_hold_id,
        hold_ids=body.hold_ids,
        color=body.color,
    )
    return analysis_out(analysis, container.media_url(analysis.image.key) or "")
