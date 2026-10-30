# Beta Climbing docs

Beta turns a photo of a boulder problem into a personalised beta and a route video.

| If you want to… | Read |
|---|---|
| Understand the product and why it exists | [Vision](product/vision.md), [PRD](product/prd.md), [Personas](product/personas.md) |
| See how the system fits together | [Architecture overview](architecture/overview.md) |
| Understand how a beta and a video are generated | [Generation pipeline](architecture/pipeline.md), [MotionSpec](architecture/motion-spec.md) |
| Work with data | [Medallion architecture](data/medallion.md), [Contracts](data/contracts.md), [Privacy](data/privacy.md) |
| Change prompts or model behaviour | [AI agents](agents/README.md) |
| Know why something is the way it is | [ADRs](adr/README.md) |
| Get the repo running | [Dev setup](guides/dev-setup.md), [Runbook](guides/runbook.md) |

Docs are code: they change in the same PR as the behaviour they describe. `make docs` serves this
site locally; `make docs-build` fails on broken links.
