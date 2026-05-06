import httpx
import pytest

from zpl_printer_emulator.config import Settings
from zpl_printer_emulator.labelary import LabelaryError, render_zpl_to_png


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
