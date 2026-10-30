# PRD — Beta v0

**Status:** in build · **Owner:** Carlos Valerio · **Last updated:** 2026-10-30

## Goal

A climber can go from photo to route video for an indoor boulder problem in under two minutes,
with a beta they rate as useful at least 60% of the time.

## User journeys

1. **Set up profile.** As a climber, I enter my height, ape index, max grade and style once, so
   every beta fits my body.
2. **Capture.** As a climber, I photograph the problem (or pick a photo), so the app can see it.
3. **Select the problem.** As a climber, I see the detected holds, pick the problem's colour or tap
   holds, and mark start and top, so the app solves the right problem.
4. **Get the beta.** As a climber, I get an ordered list of moves with technique cues, the crux and a
   grade estimate, so I know what to try.
5. **Watch it.** As a climber, I watch a video of a figure climbing my beta, stepping move by move,
   so I can see the body positions.
6. **Give feedback.** As a climber, I mark "sent it" or "move N looks wrong", so future betas improve.
7. **Logbook.** As a climber, I find past problems and their videos.

## Functional requirements

| ID | Requirement |
|---|---|
| F1 | Accept JPEG/PNG/HEIC up to 15 MB; strip GPS before storing. |
| F2 | Detect candidate holds with bbox, colour and type; group by colour. |
| F3 | Problem selection by colour or explicit hold IDs; 1–2 start holds; exactly one top hold. |
| F4 | BetaPlan references only problem hold IDs, starts on start holds, ends matched on top. |
| F5 | Every hand/foot configuration in the beta is reachable for the climber's body (2D check). |
| F6 | Up to 2 automatic repair rounds when validation fails; otherwise the beta is marked failed with reasons. |
| F7 | Video: 9:16, one chapter per move, crux slowed, captions ≤ 60 chars. |
| F8 | Works offline (no API key) with heuristic planner/director for development and CI. |
| F9 | All raw inputs/outputs land in bronze with provenance (model, prompt version, detector version). |

## Non-functional

- p50 photo → beta ≤ 30 s, beta → video ≤ 60 s (live Claude + renderer).
- Cost per beta + video ≤ US$0.10 at list prices (downscaled images, prompt caching).
- No personal data beyond a random device ID.

## Success metrics

| Metric | Source | v0 target |
|---|---|---|
| Beta validity (passes validators, ≤2 repairs) | evals | ≥ 95% |
| Useful rate ("sent it" or 👍) | gold `beta_quality` | ≥ 60% |
| "Looks wrong" per video | gold `confusing_moves` | ≤ 0.5 |
| Detection recall on golden set | evals | ≥ 0.85 |

## Risks

See the plan's risk table; the key ones are LLM spatial reasoning (mitigated by grounding +
validators), hold detection on real walls (mitigated by user selection), and climber safety
(disclaimer, confidence display).
