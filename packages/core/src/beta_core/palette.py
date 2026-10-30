"""Shared visual vocabulary. Exported to ``contracts/palette.json`` for the renderer and iOS app."""

from __future__ import annotations

from beta_core.domain.beta import Limb

#: One colour per limb, identical in overlays, route videos and the iOS move list.
LIMB_COLORS: dict[Limb, str] = {
    Limb.LH: "#3B82F6",  # blue
    Limb.RH: "#EF4444",  # red
    Limb.LF: "#14B8A6",  # teal
    Limb.RF: "#F97316",  # orange
}

#: Display colour for each detector colour label.
HOLD_COLORS: dict[str, str] = {
    "red": "#D22828",
    "orange": "#F0781E",
    "yellow": "#F0C81E",
    "green": "#28AA46",
    "blue": "#285AD2",
    "purple": "#823CB4",
    "pink": "#E65AA0",
}

ACCENT = "#FF6B35"  # chalk-on-dark theme accent
INK = "#0F1115"
CHALK = "#F5F3EE"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def palette_contract() -> dict[str, object]:
    return {
        "limbs": {limb.value: color for limb, color in LIMB_COLORS.items()},
        "holds": HOLD_COLORS,
        "accent": ACCENT,
        "ink": INK,
        "chalk": CHALK,
    }
