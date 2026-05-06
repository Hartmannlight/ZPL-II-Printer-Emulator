from __future__ import annotations

import httpx

from .config import Settings


class LabelaryError(RuntimeError):
    pass


def render_zpl_to_png(zpl: str, settings: Settings, *, client: httpx.Client | None = None) -> bytes:
    url = (
        f"{settings.labelary_url.rstrip('/')}/v1/printers/{settings.dpmm}dpmm/"
        f"labels/{settings.label_width_in}x{settings.label_height_in}/0/"
    )
    headers = {"Accept": "image/png", "Content-Type": "application/x-www-form-urlencoded"}

    owns_client = client is None
    active_client = client or httpx.Client(timeout=30)
    try:
        response = active_client.post(url, content=zpl.encode("utf-8"), headers=headers)
    except httpx.HTTPError as exc:
        raise LabelaryError(str(exc)) from exc
    finally:
        if owns_client:
            active_client.close()

    if response.status_code >= 400:
        raise LabelaryError(f"Labelary returned HTTP {response.status_code}: {response.text}")
    content_type = response.headers.get("content-type", "")
    if "image/png" not in content_type.lower():
        raise LabelaryError(f"Labelary returned unexpected content type: {content_type or 'unknown'}")
    return response.content
