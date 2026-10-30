import pytest
from pydantic import ValidationError

from beta_core.domain.grades import Grade


@pytest.mark.parametrize(
    ("text", "v"),
    [
        ("V0", 0),
        ("v5", 5),
        ("VB", -1),
        ("V17", 17),
        ("6A", 3),
        ("6c+", 5),
        ("7A", 6),
        ("8a", 11),
        (" V3 ", 3),
    ],
)
def test_parse(text: str, v: int) -> None:
    assert Grade.parse(text).v == v


@pytest.mark.parametrize("text", ["hard", "", "V99", "10Z"])
def test_parse_rejects_unknown(text: str) -> None:
    with pytest.raises(ValueError, match="grade"):
        Grade.parse(text)


def test_str_and_font() -> None:
    assert str(Grade(v=5)) == "V5"
    assert Grade(v=5).font == "6C"
    assert str(Grade(v=-1)) == "VB"


def test_ordering() -> None:
    assert Grade(v=2) < Grade(v=3)
    assert max([Grade(v=1), Grade(v=7), Grade(v=4)]) == Grade(v=7)


def test_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Grade(v=18)
