from fastapi.testclient import TestClient

from zpl_printer_emulator.app import create_app
from zpl_printer_emulator.config import Settings
from zpl_printer_emulator.store import JobStore


def test_index_exposes_emulator_controls() -> None:
    app = create_app(settings=Settings(), store=JobStore(), start_tcp=False)

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "ZPL-II Printer Emulator" in response.text
    assert "Latest label" in response.text
    assert "Continuous strip" in response.text
    assert "Print test label" in response.text


def test_static_frontend_assets_are_served() -> None:
    app = create_app(settings=Settings(), store=JobStore(), start_tcp=False)

    with TestClient(app) as client:
        script_response = client.get("/static/app.js")
        style_response = client.get("/static/styles.css")

    assert script_response.status_code == 200
    assert "zpl-printer-view-mode" in script_response.text
    assert style_response.status_code == 200
    assert ".label-strip" in style_response.text
