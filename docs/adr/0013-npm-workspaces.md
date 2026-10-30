# 0013 — npm workspaces instead of pnpm

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
The plan called for pnpm via corepack. Node 25 (installed locally) no longer bundles corepack, and
the JS side is a single package (`apps/renderer`).

## Decision
Use npm workspaces from the root `package.json`. `.nvmrc` pins Node 22 LTS for CI.

## Consequences
- No extra global tooling. Revisit pnpm if the JS side grows past a few packages.

## Alternatives considered
- *Install pnpm globally* — extra setup for one package.
