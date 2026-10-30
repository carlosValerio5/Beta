# Hold classifier

**Job:** label each detected hold's grip type (jug, crimp, sloper, pinch, pocket, edge, volume,
foothold, unknown) so the planner's hold table is richer than the colour detector's shape guess.

- **Model:** `claude-haiku-5-5`, effort `low`, no refusal fallback (not offered for Haiku).
- **Input:** set-of-marks photo of *all* detected holds, their IDs, and the detector's guesses.
- **Output:** `HoldTypeDraft {holds: [{id, hold_type}]}`; unknown IDs are ignored, missing ones
  keep the detector's guess.
- **Enabled by:** `BETA_USE_HOLD_CLASSIFIER=true` (off by default — it adds a call per upload).
- **Evaluate before enabling by default:** build a labelled set from in-app corrections (roadmap
  v0.1) and measure accuracy against the shape heuristic.
