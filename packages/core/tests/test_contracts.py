import json
from pathlib import Path

from beta_core.contracts import export_contracts
from beta_core.domain.motion import MotionSpec


def test_export_writes_schema_examples_and_fixtures(tmp_path: Path) -> None:
    written = export_contracts(tmp_path)

    schema = json.loads((tmp_path / "motion-spec" / "v1.schema.json").read_text())
    assert schema["title"] == "MotionSpec"
    assert "$defs" in schema

    example = tmp_path / "motion-spec" / "examples" / "ladder.json"
    assert MotionSpec.model_validate_json(example.read_text()).beta_id

    fixtures = json.loads((tmp_path / "kinematics" / "fixtures.json").read_text())
    assert fixtures["two_bone"]

    assert {p.relative_to(tmp_path).as_posix() for p in written} >= {
        "motion-spec/v1.schema.json",
        "motion-spec/examples/ladder.json",
        "kinematics/fixtures.json",
    }


def test_export_is_byte_stable(tmp_path: Path) -> None:
    export_contracts(tmp_path / "a")
    export_contracts(tmp_path / "b")
    for name in ["motion-spec/v1.schema.json", "motion-spec/examples/ladder.json", "kinematics/fixtures.json"]:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
