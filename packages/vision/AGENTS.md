# beta_vision — agent notes

Adapters for the image side of the hexagon. Only this package imports OpenCV.

| Module | Implements |
|---|---|
| `preprocess.py` | `PillowPreprocessor` (`ImagePreprocessor` port): EXIF transpose, GPS strip, resize ≤2048, JPEG, sha256, dHash |
| `detect.py` | `ColorHoldDetector` (`HoldDetector` port): saturation mask → contours → colour label + shape type |
| `overlay.py` | Set-of-marks image (numbered holds for Claude) and static beta poster |
| `synthetic.py` | `SyntheticWallGenerator`: seeded fake walls with ground truth, for tests/seed/evals |

Rules:
- Coordinates are pixels in the **normalised** image (after transpose + resize). Never return
  coordinates in original-upload space.
- Detector changes must keep `tests/test_detect.py` precision/recall thresholds on synthetic walls.
- Bump `ColorHoldDetector.version` whenever output can change; it is recorded in provenance.
