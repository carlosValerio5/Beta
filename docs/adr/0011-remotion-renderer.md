# 0011 — Remotion as the server-side renderer

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
We need deterministic MP4s from a JSON timeline, with good typography and easing, and a fast visual
dev loop.

## Decision
`apps/renderer` is a Remotion project. One composition (`RouteVideo`) takes a MotionSpec as input
props. A small Node HTTP service renders MP4 + poster + chapter stills. Remotion Studio previews
fixtures during development. The API talks to it through the `VideoRenderer` port.

## Consequences
- Headless Chromium + ffmpeg per render (~15–60 s); jobs are async and cached by spec hash.
- **License:** Remotion is free for individuals and small companies; larger companies need a company
  license. Re-check before commercial launch. The port lets us swap to an ffmpeg/Skia renderer.
- IK math exists in both Python (validation) and TypeScript (drawing); shared fixtures keep them equal.

## Alternatives considered
- *ffmpeg filtergraphs* — painful for typography/easing. *Native SwiftUI renderer* — no shareable MP4,
  and a second renderer to keep in sync.
