from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from beta_api import __version__
from beta_api.container import Container
from beta_api.routes import get_container
from beta_api.schemas import HealthOut
from beta_core.errors import NotFoundError

router = APIRouter(tags=["system"])
ContainerDep = Annotated[Container, Depends(get_container)]


@router.get("/health", response_model=HealthOut, summary="Liveness and active adapters")
def health(container: ContainerDep) -> HealthOut:
    d = container.describe()
    return HealthOut(
        status="ok",
        version=__version__,
        planner=str(d["planner"]),
        director=str(d["director"]),
        renderer=bool(d["renderer"]),
    )


@router.get("/media/{key:path}", summary="Images, posters and videos (supports HTTP Range)")
def media(key: str, container: ContainerDep) -> FileResponse:
    path = container.media.path(key)
    if not path.is_file():
        raise NotFoundError("media", key)
    return FileResponse(path)
