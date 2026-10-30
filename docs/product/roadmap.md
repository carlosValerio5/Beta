# Roadmap

## v0 — foundation (this build)
Monorepo, domain core, colour hold detection, Claude beta planner + motion director, Remotion route
videos, SwiftUI app, medallion data, offline evals.

## v0.1 — real walls
- Collect real photos with consent; label holds via in-app corrections → gold training set.
- Train a YOLO-seg hold detector behind the `HoldDetector` port; A/B against the colour detector.
- Wall-angle estimation (slab / vertical / overhang) as planner input.

## v0.2 — better movement
- Technique-specific figure poses (heel hook, drop knee) with 2.5D cues.
- Alternative betas side by side ("short", "dynamic", "static").
- Voice-over from captions (TTS), optional.

## v0.3 — community
- Accounts, sharing videos, "verified send" betas weighted higher in gold.
- Setter mode: intended beta vs. model beta.

## Later
Outdoor mode with topo-aware problem selection; on-device detection; Android.
