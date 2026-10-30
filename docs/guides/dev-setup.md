# Dev setup

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| uv ≥ 0.12 | Python workspace | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node ≥ 22 | renderer | `brew install node@22` |
| ffmpeg | renderer output checks | `brew install ffmpeg` |
| Xcode 16+ | iOS app build + simulator | App Store, then `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` |
| xcodegen, swiftlint, swiftformat | iOS project + lint | `brew install xcodegen swiftlint swiftformat` |

Without Xcode you can still run `make test-swift` (BetaKit logic) with the Command Line Tools.

## First run

```bash
make bootstrap
cp .env.example .env        # optional ANTHROPIC_API_KEY
make test
make seed data              # synthetic data through the medallion layers
make dev                    # API :8000 (docs at /docs), renderer :8787
```

## iOS

```bash
make ios-project            # generates apps/ios/Beta.xcodeproj
open apps/ios/Beta.xcodeproj
```

The simulator reaches the API at `http://localhost:8000`. On a physical device set the API base URL
in the app's Settings screen to your Mac's LAN address.
