# 0007 — Strip GPS at ingress, all EXIF at silver

- **Status:** Accepted
- **Date:** 2026-10-30

## Context
Phone photos carry GPS coordinates and device metadata, and may include people. Bronze is meant to
be "raw", but storing home/gym locations is a liability we don't need.

## Decision
- GPS EXIF is removed **before** the upload touches disk, including bronze. When GPS was present we
  record `gps_stripped: true` in the event.
- Silver images carry **no** EXIF at all (re-encoded after orientation is applied).
- Clients are identified by a random device UUID; no names, emails or accounts in v0.

## Consequences
- Bronze is "raw minus GPS". Documented in [privacy](../data/privacy.md).
- Re-encoding is only done when GPS exists, so most bronze images are byte-identical to uploads.

## Alternatives considered
- *Keep raw, restrict access* — one leak away from exposing locations.
