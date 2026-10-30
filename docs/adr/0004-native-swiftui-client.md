# 0004 — Native SwiftUI iOS client

- **Status:** Accepted (replaces the Expo proposal from the first plan draft)
- **Date:** 2026-10-30

## Context
The core interaction is camera → tap holds → watch a video. The product owner chose native iOS for
camera quality and feel.

## Decision
A SwiftUI app (iOS 18+, Swift 6 strict concurrency). Logic that doesn't need UIKit — models, API
client, view-model state machines — lives in the `BetaKit` Swift package so it is testable with
`swift test` on macOS without Xcode. Videos are rendered server-side and played with AVPlayer;
chapter times from the MotionSpec drive move-by-move stepping.

## Consequences
- iOS only for now; Android would be a second client against the same API.
- Building the app and running the simulator requires Xcode (not just Command Line Tools).
- BetaKit models are hand-written Codable types checked against `contracts/api/examples/*.json`.

## Alternatives considered
- *Expo / React Native* — cross-platform, but camera and video polish cost more; owner preferred native.
- *Next.js PWA* — could play Remotion live, but weaker camera UX and no App Store presence.
