# 0012 — XcodeGen for the iOS project

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
`.xcodeproj` files are machine-written, merge badly and are hard for agents to edit safely.

## Decision
`apps/ios/project.yml` is the source of truth; `xcodegen generate` produces `Beta.xcodeproj`, which
is gitignored. Shared logic is in the local `BetaKit` Swift package.

## Consequences
- Contributors need `brew install xcodegen`.
- Project changes are reviewable YAML diffs.

## Alternatives considered
- *Tuist* — more powerful, more to learn. *Committed .xcodeproj* — merge conflicts.
