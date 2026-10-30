# 0003 — FastAPI backend

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
The backend must sit next to Python CV and data code, accept image uploads, run long jobs, and
publish an OpenAPI document that the iOS client mirrors.

## Decision
FastAPI with Pydantic v2, served by uvicorn. v0 persistence is SQLite (one table per aggregate,
JSON payloads) behind repository ports; media on local disk behind a store port.

## Consequences
- OpenAPI comes free and is exported to `contracts/openapi.json`.
- SQLite limits us to one API process; acceptable for v0, swap via the repository port later.

## Alternatives considered
- *Django* — heavier, ORM we don't need. *Node backend* — splits the CV/LLM code from the API.
