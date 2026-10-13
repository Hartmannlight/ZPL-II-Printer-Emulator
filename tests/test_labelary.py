import httpx
import pytest

from zpl_printer_emulator.config import Settings
from zpl_printer_emulator.labelary import LabelaryError, render_zpl_to_png
from zpl_printer_emulator import labelary


@pytest.fixture(autouse=True)
def reset_pacing(monkeypatch):
    monkeypatch.setattr(labelary, '_next_request_at', 0.0)
    monkeypatch.setattr(labelary, '_MIN_INTERVAL_SECONDS', 0)


def test_render_zpl_to_png_posts_to_labelary() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"png")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(labelary_url="https://labelary.test", dpmm=8)

    assert render_zpl_to_png("^XA^XZ", settings, client=client) == b"png"
    assert requests[0].url.path == "/v1/printers/8dpmm/labels/1.9685x0.9843/0/"
    assert requests[0].content == b"^XA^XZ"
    assert requests[0].headers["accept"] == "image/png"


def test_render_zpl_to_png_rejects_non_png_response() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/plain"}, text="ok")
        )
    )

    with pytest.raises(LabelaryError, match="unexpected content type"):
        render_zpl_to_png("^XA^XZ", Settings(), client=client)


@pytest.mark.parametrize('status', [429, 502, 503, 504])
def test_transient_render_failure_retries_same_label_and_honors_retry_after(monkeypatch, status):
    calls = []
    delays = []

    def handler(request):
        calls.append(request.content)
        if len(calls) == 1:
            return httpx.Response(status, headers={'Retry-After': '2'}, text='busy')
        return httpx.Response(200, headers={'content-type': 'image/png'}, content=b'png')

    monkeypatch.setattr(labelary.time, 'sleep', delays.append)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert render_zpl_to_png('^XA^FDONE^FS^XZ', Settings(), client=client) == b'png'
    assert calls == [b'^XA^FDONE^FS^XZ'] * 2
    assert delays == [2]


def test_persistent_rate_limit_stops_after_bounded_retries(monkeypatch):
    calls = []
    delays = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, text='Request rate limit exceeded')

    monkeypatch.setattr(labelary.time, 'sleep', delays.append)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LabelaryError, match='HTTP 429'):
            render_zpl_to_png('^XA^XZ', Settings(), client=client)
    assert len(calls) == 5
    assert delays == [1, 2, 4, 8]


def test_invalid_zpl_is_not_retried(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, text='Invalid ZPL')

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LabelaryError, match='HTTP 400'):
            render_zpl_to_png('invalid', Settings(), client=client)
    assert len(calls) == 1


def test_concurrent_render_requests_are_paced_across_connections(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    clock = [0.0]
    starts = []
    monkeypatch.setattr(labelary, '_MIN_INTERVAL_SECONDS', .5)
    monkeypatch.setattr(labelary.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(labelary.time, 'sleep', lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    def handler(_request):
        starts.append(clock[0])
        return httpx.Response(200, headers={'content-type': 'image/png'}, content=b'png')

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(lambda _: render_zpl_to_png('^XA^XZ', Settings(), client=client), range(4)))
    assert results == [b'png'] * 4
    assert starts == [0, .5, 1, 1.5]
