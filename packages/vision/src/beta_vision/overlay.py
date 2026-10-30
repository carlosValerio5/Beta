"""Image overlays: set-of-marks for Claude, and a static beta poster (video fallback / thumbnail)."""

from __future__ import annotations

import hashlib
import io
from collections.abc import Sequence

from PIL import Image, ImageDraw, ImageFont

from beta_core.domain.beta import BetaPlan, Limb
from beta_core.domain.holds import Hold, Problem
from beta_core.palette import LIMB_COLORS, hex_to_rgb
from beta_core.ports import NormalizedImage
from beta_vision.preprocess import dhash

WHITE = (255, 255, 255)
BLACK = (15, 17, 21)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _encode(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _badge(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    radius: float,
    text: str,
    fill: tuple[int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius], fill=fill, outline=WHITE, width=2
    )
    draw.text((x, y), text, fill=WHITE, font=font, anchor="mm")


class PillowMarkRenderer:
    """Numbered markers on each hold — the IDs Claude must use in its answer (ADR-0005)."""

    def render_marks(self, image: NormalizedImage, holds: Sequence[Hold]) -> NormalizedImage:
        img = Image.open(io.BytesIO(image.data)).convert("RGB")
        draw = ImageDraw.Draw(img)
        scale = max(img.size) / 1000
        font = _font(max(12, int(18 * scale)))
        badge_r = 13 * scale
        for hold in holds:
            c = hold.center
            r = hold.size / 2 + 4 * scale
            draw.ellipse(
                [c.x - r, c.y - r, c.x + r, c.y + r], outline=WHITE, width=max(2, int(3 * scale))
            )
            _badge(draw, c.x + r * 0.75, c.y - r * 0.75, badge_r, str(hold.id), BLACK, font)
        data = _encode(img)
        return NormalizedImage(
            data=data,
            width=img.width,
            height=img.height,
            sha256=hashlib.sha256(data).hexdigest(),
            dhash=dhash(img),
        )


def render_beta_poster(image: NormalizedImage, plan: BetaPlan, problem: Problem) -> bytes:
    """Static summary of a beta: per-limb paths, numbered move targets, start and top labels."""
    img = Image.open(io.BytesIO(image.data)).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    scale = max(img.size) / 1000
    font = _font(max(11, int(16 * scale)))
    width = max(3, int(5 * scale))

    for limb in Limb:
        path = [
            problem.hold(h).center
            for h in [plan.start.get(limb), *(m.hold_id for m in plan.moves if m.limb is limb)]
            if h is not None
        ]
        if len(path) > 1:
            rgb = hex_to_rgb(LIMB_COLORS[limb])
            draw.line([(p.x, p.y) for p in path], fill=(*rgb, 200), width=width, joint="curve")

    for start_id in problem.start_hold_ids:
        c = problem.hold(start_id).center
        _badge(draw, c.x, c.y, 15 * scale, "S", BLACK, font)
    top = problem.hold(problem.top_hold_id).center
    _badge(draw, top.x, top.y - 22 * scale, 18 * scale, "TOP", BLACK, font)

    for move in plan.moves:
        c = problem.hold(move.hold_id).center
        offset = {Limb.LH: (-1, -1), Limb.RH: (1, -1), Limb.LF: (-1, 1), Limb.RF: (1, 1)}[move.limb]
        x = c.x + offset[0] * 16 * scale
        y = c.y + offset[1] * 16 * scale
        _badge(
            draw, x, y, 11 * scale, str(move.index + 1), hex_to_rgb(LIMB_COLORS[move.limb]), font
        )
    return _encode(img)
