# 0008 — Async generation jobs with polling

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Beta planning with a vision model takes 10–30 s; directing + rendering a video up to a minute.
Mobile connections drop.

## Decision
`POST` endpoints for betas and videos return **202** with a resource whose `status` advances
(`pending → ready|failed` for betas; `directing → rendering → ready|failed` for videos). Work runs
in background tasks in the API process. Clients poll `GET` with backoff.

## Consequences
- Simple and testable; no broker in v0.
- Jobs die with the process. A queue (e.g. Redis + worker) replaces `BackgroundTasks` behind the
  same use cases when we need durability.

## Alternatives considered
- *Synchronous requests* — timeouts on mobile. *SSE/WebSockets* — nicer UX, more moving parts.
