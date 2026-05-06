from fastapi.testclient import TestClient

from zpl_printer_emulator.app import create_app
from zpl_printer_emulator.config import Settings
from zpl_printer_emulator.store import JobStore


def fake_renderer(zpl: str, settings: Settings) -> bytes:
    assert zpl.startswith("^XA")
    assert settings.dpmm == 8
    return b"png"


def test_test_print_creates_rendered_job() -> None:
    store = JobStore()
    app = create_app(settings=Settings(), store=store, renderer=fake_renderer, start_tcp=False)

    with TestClient(app) as client:
        response = client.post("/api/test-print", json={"zpl": "^XA^XZ"})
        assert response.status_code == 200
        job_id = response.json()["id"]

        image_response = client.get(f"/api/jobs/{job_id}/image")
        assert image_response.status_code == 200
        assert image_response.content == b"png"


def test_missing_job_returns_404() -> None:
    app = create_app(settings=Settings(), store=JobStore(), renderer=fake_renderer, start_tcp=False)

    with TestClient(app) as client:
        response = client.get("/api/jobs/missing")

    assert response.status_code == 404
