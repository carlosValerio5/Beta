"""Upload sanitisation (GPS strip, ADR-0007) and normalisation (orient, resize, EXIF-free JPEG)."""

from __future__ import annotations

import hashlib
import io

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from beta_core.errors import InvalidInputError
from beta_core.ports import NormalizedImage, SanitizedUpload

GPS_IFD = 0x8825
DEFAULT_MAX_SIDE = 2048
CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "MPO": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _open(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Image.DecompressionBombError as exc:
        raise InvalidInputError("image is too large") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidInputError("upload is not a readable image") from exc
    return img


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dhash(img: Image.Image) -> str:
    """64-bit difference hash: robust to brightness/compression, sensitive to layout."""
    gray = np.asarray(img.convert("L").resize((9, 8), Image.Resampling.LANCZOS), dtype=np.int16)
    value = 0
    for bit in (gray[:, :-1] > gray[:, 1:]).flatten():
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


class PillowPreprocessor:
    def __init__(self, max_side: int = DEFAULT_MAX_SIDE, jpeg_quality: int = 90) -> None:
        self.max_side = max_side
        self.jpeg_quality = jpeg_quality

    def sanitize(self, raw: bytes) -> SanitizedUpload:
        img = _open(raw)
        fmt = img.format or ""
        content_type = CONTENT_TYPES.get(fmt)
        if content_type is None:
            raise InvalidInputError(
                f"unsupported image format {fmt or 'unknown'}; send JPEG, PNG or WebP"
            )
        exif = img.getexif()
        if GPS_IFD not in exif:
            return SanitizedUpload(
                data=raw, sha256=_sha256(raw), content_type=content_type, gps_stripped=False
            )

        del exif[GPS_IFD]
        buf = io.BytesIO()
        save_format = "JPEG" if fmt == "MPO" else fmt
        if save_format == "JPEG":
            img.save(buf, format=save_format, exif=exif.tobytes(), quality=95)
        else:
            img.save(buf, format=save_format, exif=exif.tobytes())
        data = buf.getvalue()
        return SanitizedUpload(
            data=data, sha256=_sha256(data), content_type=content_type, gps_stripped=True
        )

    def normalize(self, data: bytes) -> NormalizedImage:
        img = ImageOps.exif_transpose(_open(data)).convert("RGB")
        img.thumbnail((self.max_side, self.max_side), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.jpeg_quality, optimize=True)
        out = buf.getvalue()
        return NormalizedImage(
            data=out, width=img.width, height=img.height, sha256=_sha256(out), dhash=dhash(img)
        )
