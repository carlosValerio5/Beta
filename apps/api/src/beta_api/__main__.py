"""``beta-api`` / ``python -m beta_api``: serve the API with uvicorn."""

from __future__ import annotations

import logging

import uvicorn

from beta_api.app import create_app
from beta_api.settings import Settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
