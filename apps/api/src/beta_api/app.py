from __future__ import annotations

from fastapi import FastAPI

from beta_api import __version__
from beta_api.container import Container
from beta_api.errors import install_error_handlers
from beta_api.routes import analyses, betas, system, videos
from beta_api.settings import Settings

DESCRIPTION = """
Photograph a boulder, pick the problem, get a beta and a route video.

Flow: `POST /v1/analyses` → `PUT /v1/analyses/{id}/problem` → `POST /v1/analyses/{id}/betas`
(202, poll) → `POST /v1/betas/{id}/videos` (202, poll) → `POST /v1/betas/{id}/feedback`.
"""


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    app = FastAPI(title="Beta Climbing API", version=__version__, description=DESCRIPTION)
    app.state.container = container or Container(settings)
    install_error_handlers(app)
    for module in (system, analyses, betas, videos):
        app.include_router(module.router)
    return app
