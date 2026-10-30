# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Monorepo scaffolding: uv + npm workspaces, Makefile, CI, pre-commit, docs site, ADRs 0001–0013.
- `beta_core`: domain model, ports, use cases, BetaPlan + MotionSpec validators, 2D kinematics.
- `beta_vision`: preprocessing (EXIF/GPS stripping, normalisation, dHash), colour hold detector,
  set-of-marks and beta overlays, synthetic wall generator.
- `beta_llm`: versioned prompt registry, Claude beta planner / motion director / hold classifier,
  heuristic offline planner and choreography director.
- `beta_data`: medallion lakehouse (bronze/silver/gold), contracts, lineage manifests, CLI, DVC stages.
- `beta_api`: FastAPI v1 (analyses, problems, betas, videos, feedback, media) with background jobs.
- `@beta/renderer`: Remotion route-video composition with 2D IK climber, render service.
- iOS: SwiftUI app and `BetaKit` package.
- `beta_evals`: offline/cassette/live eval harness over the golden set with a threshold gate.
- `scripts/e2e_smoke.py` / `make smoke`: live HTTP run from photo to rendered MP4.
- DVC: `data/bronze` tracked, `dvc.yaml` stages reproduced (`dvc.lock`).
- Docs: architecture (overview, hexagonal, pipeline, MotionSpec, kinematics), AI agent docs,
  runbook, generated table contracts, TDD evidence report.
