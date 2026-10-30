# Beta Climbing — single entrypoint for every workflow.
# Run `make help` to list targets.

SHELL := /bin/bash
.DEFAULT_GOAL := help

UV        ?= uv
NPM       ?= npm
DVC       ?= uvx --from dvc dvc
BETAKIT   := apps/ios/Packages/BetaKit
IOS_SIM   ?= iPhone 16

.PHONY: help
help: ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- setup
.PHONY: bootstrap
bootstrap: ## Install Python + JS deps and git hooks
	$(UV) sync --all-groups
	$(NPM) install
	$(UV) run pre-commit install

# ---------------------------------------------------------------- quality
.PHONY: lint fmt typecheck
lint: ## Lint Python + TypeScript (+ Swift when swiftlint is installed)
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(NPM) run lint
	@command -v swiftlint >/dev/null && swiftlint lint --quiet apps/ios || echo "swiftlint not installed; skipping"

fmt: ## Auto-format everything
	$(UV) run ruff check --fix .
	$(UV) run ruff format .
	@command -v swiftformat >/dev/null && swiftformat apps/ios || true

typecheck: ## mypy (strict) + tsc
	$(UV) run mypy packages/core/src packages/vision/src packages/llm/src packages/data/src apps/api/src evals/src
	$(NPM) run typecheck

# ---------------------------------------------------------------- tests
.PHONY: test test-py test-js test-swift coverage
test: test-py test-js test-swift ## Run every test suite

test-py: ## Python tests
	$(UV) run pytest

test-js: ## Renderer tests (vitest)
	$(NPM) test

test-swift: ## BetaKit Swift package tests (runs on macOS, no Xcode needed)
	swift test --package-path $(BETAKIT)

coverage: ## Python coverage gate (80%)
	$(UV) run pytest --cov --cov-report=term-missing

# ---------------------------------------------------------------- contracts
.PHONY: contracts contracts-check
contracts: ## Regenerate JSON Schema / OpenAPI / fixtures in contracts/
	$(UV) run python -m beta_core.contracts contracts
	$(UV) run python -m beta_api.openapi contracts/openapi.json
	$(UV) run beta-data contracts-doc

contracts-check: contracts ## Fail if generated contracts drifted from source
	git diff --exit-code -- contracts

# ---------------------------------------------------------------- data (medallion)
.PHONY: seed data bronze-to-silver silver-to-gold dvc-init dvc-repro
seed: ## Generate synthetic walls into bronze
	$(UV) run beta-data seed --count 12

bronze-to-silver: ## Bronze -> silver
	$(UV) run beta-data run bronze-to-silver

silver-to-gold: ## Silver -> gold
	$(UV) run beta-data run silver-to-gold

data: bronze-to-silver silver-to-gold ## Run the whole medallion pipeline

dvc-init: ## Initialise DVC with a local remote (one-off)
	$(DVC) init -q || true
	$(DVC) remote add -d -f local ../.beta-dvc-remote

dvc-repro: ## Reproduce the pipeline declared in dvc.yaml
	$(DVC) repro

# ---------------------------------------------------------------- evals
.PHONY: eval eval-live
eval: ## Offline eval on the golden set (heuristic adapters / cassettes)
	$(UV) run beta-eval run --offline

eval-live: ## Live eval against Claude (needs ANTHROPIC_API_KEY)
	BETA_LIVE=1 $(UV) run beta-eval run

# ---------------------------------------------------------------- run
.PHONY: api renderer studio render-fixture dev smoke
api: ## Run the API on :8000
	$(UV) run beta-api

renderer: ## Run the Remotion render service on :8787
	$(NPM) run start -w @beta/renderer

studio: ## Open Remotion Studio with fixture specs
	$(NPM) run studio -w @beta/renderer

render-fixture: ## Render the golden MotionSpec fixture to var/renders/
	$(NPM) run render:fixture -w @beta/renderer

smoke: ## End-to-end HTTP smoke test against a running `make dev`
	$(UV) run python scripts/e2e_smoke.py

dev: ## API + renderer together
	$(MAKE) -j2 api renderer

# ---------------------------------------------------------------- iOS
.PHONY: ios ios-project
ios-project: ## Generate the Xcode project (needs xcodegen)
	cd apps/ios && xcodegen generate

ios: ios-project ## Build + test the iOS app on the simulator (needs Xcode)
	cd apps/ios && xcodebuild -project Beta.xcodeproj -scheme Beta \
	  -destination 'platform=iOS Simulator,name=$(IOS_SIM)' test

# ---------------------------------------------------------------- docs
.PHONY: docs docs-build
docs: ## Serve the docs site
	$(UV) run --group docs mkdocs serve

docs-build: ## Build the docs site (strict)
	$(UV) run --group docs mkdocs build --strict

# ---------------------------------------------------------------- all
.PHONY: check
check: lint typecheck test contracts-check eval ## Everything CI runs
