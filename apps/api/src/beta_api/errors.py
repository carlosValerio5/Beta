"""Map domain errors to HTTP. Body shape: ``{"error": {"code": str, "message": str}}``."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from beta_core.errors import (
    AdapterError,
    InvalidInputError,
    InvalidStateError,
    NotFoundError,
    UnknownHoldError,
)

_STATUS: tuple[tuple[type[Exception], int, str], ...] = (
    (UnknownHoldError, 422, "unknown_hold"),
    (NotFoundError, 404, "not_found"),
    (InvalidStateError, 409, "invalid_state"),
    (InvalidInputError, 422, "invalid_input"),
    (AdapterError, 502, "upstream_error"),
    (ValueError, 422, "invalid_input"),  # includes pydantic.ValidationError from domain models
)


def install_error_handlers(app: FastAPI) -> None:
    for exc_type, status, code in _STATUS:

        async def handler(
            _: Request, exc: Exception, status: int = status, code: str = code
        ) -> JSONResponse:
            return JSONResponse(
                status_code=status, content={"error": {"code": code, "message": str(exc)}}
            )

        app.add_exception_handler(exc_type, handler)
