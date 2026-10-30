"""``VideoRenderer`` adapter for the Remotion render service (apps/renderer, ADR-0011)."""

from __future__ import annotations

import base64

import httpx

from beta_core.domain.motion import MotionSpec
from beta_core.errors import AdapterError
from beta_core.ports import MediaStore, RenderResult

DEFAULT_TIMEOUT_S = 600.0


class RemotionHttpRenderer:
    def __init__(
        self,
        base_url: str,
        media: MediaStore,
        *,
        client: httpx.Client | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._media = media
        self._client = client or httpx.Client()
        self._timeout = timeout_s

    def render(self, spec: MotionSpec, video_id: str) -> RenderResult:
        image = base64.b64encode(self._media.get(spec.image.uri)).decode("ascii")
        payload = {
            "video_id": video_id,
            "spec": spec.model_dump(mode="json"),
            "image_data_url": f"data:image/jpeg;base64,{image}",
        }
        try:
            response = self._client.post(
                f"{self._base_url}/render", json=payload, timeout=self._timeout
            )
        except httpx.HTTPError as exc:
            raise AdapterError(f"renderer unreachable: {exc}") from exc
        if response.status_code != httpx.codes.OK:
            raise AdapterError(f"renderer returned {response.status_code}: {response.text[:200]}")
        body = response.json()
        video_key, poster_key = f"videos/{video_id}.mp4", f"videos/{video_id}.jpg"
        self._media.put(video_key, base64.b64decode(body["video_base64"]), "video/mp4")
        self._media.put(poster_key, base64.b64decode(body["poster_base64"]), "image/jpeg")
        return RenderResult(
            video_key=video_key, poster_key=poster_key, duration_s=float(body["duration_s"])
        )
