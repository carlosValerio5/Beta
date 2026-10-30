from __future__ import annotations

import io

import pytest
from PIL import Image, ImageEnhance

from beta_core.errors import InvalidInputError
from beta_vision.preprocess import (
    GPS_IFD,
    PillowPreprocessor,
    dhash,
    hamming,
)

MAKE = 0x010F
ORIENTATION = 0x0112


def jpeg(img: Image.Image, exif: Image.Exif | None = None) -> bytes:
    buf = io.BytesIO()
    if exif is None:
        img.save(buf, format="JPEG", quality=92)
    else:
        img.save(buf, format="JPEG", quality=92, exif=exif)
    return buf.getvalue()


def gradient(w: int = 320, h: int = 240) -> Image.Image:
    img = Image.new("RGB", (w, h))
    img.putdata([(x * 255 // w, y * 255 // h, 128) for y in range(h) for x in range(w)])
    return img


def test_sanitize_strips_gps_but_keeps_other_tags() -> None:
    exif = Image.Exif()
    exif[MAKE] = "TestCam"
    exif[GPS_IFD] = {1: "N", 2: (0.0, 0.0, 0.0)}
    raw = jpeg(gradient(), exif)
    assert Image.open(io.BytesIO(raw)).getexif().get_ifd(GPS_IFD)

    out = PillowPreprocessor().sanitize(raw)

    assert out.gps_stripped
    cleaned = Image.open(io.BytesIO(out.data)).getexif()
    assert not cleaned.get_ifd(GPS_IFD)
    assert cleaned.get(MAKE) == "TestCam"
    assert out.content_type == "image/jpeg"


def test_sanitize_without_gps_keeps_bytes() -> None:
    raw = jpeg(gradient())
    out = PillowPreprocessor().sanitize(raw)
    assert not out.gps_stripped
    assert out.data == raw
    assert len(out.sha256) == 64


def test_sanitize_accepts_png() -> None:
    buf = io.BytesIO()
    gradient().save(buf, format="PNG")
    assert PillowPreprocessor().sanitize(buf.getvalue()).content_type == "image/png"


def test_sanitize_rejects_non_images() -> None:
    with pytest.raises(InvalidInputError, match="image"):
        PillowPreprocessor().sanitize(b"definitely not an image")


def test_normalize_applies_exif_orientation() -> None:
    exif = Image.Exif()
    exif[ORIENTATION] = 6  # rotate 90° clockwise on display
    raw = jpeg(gradient(200, 100), exif)
    out = PillowPreprocessor().normalize(raw)
    assert (out.width, out.height) == (100, 200)


def test_normalize_caps_longest_side() -> None:
    out = PillowPreprocessor(max_side=2048).normalize(jpeg(gradient(3000, 1000)))
    assert max(out.width, out.height) == 2048
    assert out.height == 683


def test_normalize_drops_all_exif() -> None:
    exif = Image.Exif()
    exif[MAKE] = "TestCam"
    out = PillowPreprocessor().normalize(jpeg(gradient(), exif))
    assert not Image.open(io.BytesIO(out.data)).getexif()
    assert out.content_type == "image/jpeg"


def test_dhash_is_robust_to_brightness_but_not_content() -> None:
    base = gradient()
    brighter = ImageEnhance.Brightness(base).enhance(1.15)
    other = gradient().transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    assert hamming(dhash(base), dhash(brighter)) <= 4
    assert hamming(dhash(base), dhash(other)) >= 10
    assert len(dhash(base)) == 16
