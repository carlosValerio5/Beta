from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from beta_api.container import Container
from beta_api.routes import get_container
from beta_api.schemas import VideoOut, video_out
from beta_core.errors import InvalidStateError

router = APIRouter(prefix="/v1", tags=["videos"])
ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/videos/{video_id}", response_model=VideoOut, summary="Get a route video")
def get_video(video_id: str, container: ContainerDep) -> VideoOut:
    v = container.videos.get(video_id)
    return video_out(v, container.media_url(v.video_key), container.media_url(v.poster_key))


@router.get("/videos/{video_id}/spec", summary="The MotionSpec behind a video (debugging, Studio)")
def get_video_spec(video_id: str, container: ContainerDep) -> dict[str, Any]:
    v = container.videos.get(video_id)
    if v.spec is None:
        raise InvalidStateError("the video has not been directed yet")
    return v.spec.model_dump(mode="json")
