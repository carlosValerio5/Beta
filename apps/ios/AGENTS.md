# apps/ios — agent notes

SwiftUI app (iOS 18, Swift 6 strict concurrency) + the `BetaKit` package.

| Path | What |
|---|---|
| `project.yml` | XcodeGen spec — the source of truth for the Xcode project (ADR-0012) |
| `Packages/BetaKit` | UIKit-free core: wire models, `BetaClient`, `Poller`, `HoldSelection`, `ChapterTimeline`, `ClimbSession`, `Palette` |
| `BetaApp/` | Views only: capture, hold review, beta, route video player, logbook, profile |
| `BetaUITests/` | Launch smoke test |

Rules:
- Logic goes in BetaKit with Swift Testing tests (`make test-swift` runs without Xcode). Views stay
  thin: read `ClimbSession`, call its async methods.
- BetaKit models mirror `apps/api/src/beta_api/schemas.py`; `ContractDecodingTests` decodes
  `contracts/api/examples/*.json`. API change → `make contracts` → fix models → tests green.
- Colours come from `Palette` (mirrors `contracts/palette.json`), never literals in views.
- Building the app and running the simulator needs Xcode + `brew install xcodegen`
  (`make ios`). The simulator reaches the API at `http://localhost:8000`.
