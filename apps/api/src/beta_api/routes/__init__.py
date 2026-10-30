"""HTTP routers. Thin: parse, call a use case, map to a wire schema."""

from __future__ import annotations

from fastapi import Request

from beta_api.container import Container


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container
