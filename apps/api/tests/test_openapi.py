from __future__ import annotations

import json
from pathlib import Path

from beta_api.app import create_app
from beta_api.openapi import export_contracts


def test_openapi_lists_the_v1_surface() -> None:
    spec = create_app().openapi()
    paths = set(spec["paths"])
    assert {
        "/health",
        "/v1/analyses",
        "/v1/analyses/{analysis_id}",
        "/v1/analyses/{analysis_id}/problem",
        "/v1/analyses/{analysis_id}/betas",
        "/v1/betas/{beta_id}",
        "/v1/betas/{beta_id}/feedback",
        "/v1/betas/{beta_id}/videos",
        "/v1/videos/{video_id}",
        "/v1/videos/{video_id}/spec",
    } <= paths
    assert {"AnalysisOut", "BetaOut", "VideoOut"} <= set(spec["components"]["schemas"])


def test_export_writes_openapi_and_deterministic_examples(tmp_path: Path) -> None:
    export_contracts(tmp_path / "a")
    export_contracts(tmp_path / "b")
    for name in ("openapi.json", "api/examples/analysis.json", "api/examples/beta.json", "api/examples/video.json"):
        a = (tmp_path / "a" / name).read_bytes()
        assert a == (tmp_path / "b" / name).read_bytes(), name
    beta = json.loads((tmp_path / "a" / "api/examples/beta.json").read_text())
    assert beta["status"] == "ready"
    video = json.loads((tmp_path / "a" / "api/examples/video.json").read_text())
    assert video["chapters"]
