from __future__ import annotations

import logging
from threading import Lock
import time

import httpx

from .config import Settings


class LabelaryError(RuntimeError):
    pass


_logger = logging.getLogger(__name__)
_request_lock = Lock()
_next_request_at = 0.0
_MIN_INTERVAL_SECONDS = 0.5
_MAX_ATTEMPTS = 5
_RETRYABLE_STATUSES = {429, 502, 503, 504}


def _post_paced(client: httpx.Client, url: str, zpl: str, headers: dict[str, str]):
    global _next_request_at
    # Keep all callers below Labelary's free-plan limit, including separate
    # TCP connections. Studio previews may still share the same public IP.
    with _request_lock:
        delay = _next_request_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        _next_request_at = time.monotonic() + _MIN_INTERVAL_SECONDS
        return client.post(url, content=zpl.encode('utf-8'), headers=headers)


def _retry_delay(response: httpx.Response | None, attempt: int) -> float:
    delay = float(2 ** attempt)
    if response is not None:
        retry_after = response.headers.get('retry-after')
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                from datetime import datetime, timezone
                from email.utils import parsedate_to_datetime
                try:
                    delay = max(delay, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
    return min(delay, 30.0)


def render_zpl_to_png(zpl: str, settings: Settings, *, client: httpx.Client | None = None) -> bytes:
    url = (
        f"{settings.labelary_url.rstrip('/')}/v1/printers/{settings.dpmm}dpmm/"
        f"labels/{settings.label_width_in}x{settings.label_height_in}/0/"
    )
    headers = {"Accept": "image/png", "Content-Type": "application/x-www-form-urlencoded"}

    owns_client = client is None
    active_client = client or httpx.Client(timeout=30)
    try:
        for attempt in range(_MAX_ATTEMPTS):
            response = None
            try:
                response = _post_paced(active_client, url, zpl, headers)
            except httpx.HTTPError as exc:
                if attempt == _MAX_ATTEMPTS - 1:
                    raise LabelaryError(str(exc)) from exc
            else:
                if response.status_code not in _RETRYABLE_STATUSES or attempt == _MAX_ATTEMPTS - 1:
                    break
            delay = _retry_delay(response, attempt)
            _logger.warning('Labelary render retry %s/%s after %ss (HTTP %s)',
                            attempt + 1, _MAX_ATTEMPTS - 1, delay,
                            response.status_code if response is not None else 'connection error')
            time.sleep(delay)
    finally:
        if owns_client:
            active_client.close()

    if response.status_code >= 400:
        raise LabelaryError(f"Labelary returned HTTP {response.status_code}: {response.text}")
    content_type = response.headers.get("content-type", "")
    if "image/png" not in content_type.lower():
        raise LabelaryError(f"Labelary returned unexpected content type: {content_type or 'unknown'}")
    return response.content
