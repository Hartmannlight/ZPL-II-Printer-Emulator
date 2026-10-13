from fastapi.testclient import TestClient

from zpl_printer_emulator.app import create_app
from zpl_printer_emulator.config import Settings
from zpl_printer_emulator.store import JobStore
import asyncio


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


def test_tcp_status_queries_do_not_create_print_jobs(monkeypatch) -> None:
    handlers = []

    class FakeTcpServer:
        def __init__(self, host, port, handler):
            handlers.append(handler)

        async def start(self):
            pass

        async def stop(self):
            pass

    monkeypatch.setattr('zpl_printer_emulator.app.TcpPrinterServer', FakeTcpServer)
    app = create_app(settings=Settings(), store=JobStore(), renderer=fake_renderer)
    with TestClient(app) as client:
        asyncio.run(handlers[0](b'~HS'))
        asyncio.run(handlers[0](b'~HQES'))
        assert client.get('/api/jobs').json() == []


def test_printer_settings_can_be_updated_for_new_jobs() -> None:
    seen_settings: list[Settings] = []

    def renderer(zpl: str, settings: Settings) -> bytes:
        seen_settings.append(settings)
        return b"png"

    app = create_app(settings=Settings(), store=JobStore(), renderer=renderer, start_tcp=False)

    with TestClient(app) as client:
        settings_response = client.get("/api/settings")
        assert settings_response.status_code == 200
        assert settings_response.json() == {
            "label_width_mm": 50.0,
            "label_height_mm": 25.0,
            "dpmm": 8,
        }

        update_response = client.put(
            "/api/settings",
            json={"label_width_mm": 100, "label_height_mm": 50, "dpmm": 12},
        )
        assert update_response.status_code == 200
        assert update_response.json() == {
            "label_width_mm": 100.0,
            "label_height_mm": 50.0,
            "dpmm": 12,
        }

        print_response = client.post("/api/test-print", json={"zpl": "^XA^XZ"})
        assert print_response.status_code == 200

    assert seen_settings[-1].dpmm == 12
    assert round(seen_settings[-1].label_width_in * 25.4) == 100
    assert round(seen_settings[-1].label_height_in * 25.4) == 50


def test_tcp_payload_with_multiple_labels_creates_one_image_job_per_label(monkeypatch) -> None:
    handlers = []

    class FakeTcpServer:
        def __init__(self, host, port, handler):
            handlers.append(handler)

        async def start(self):
            pass

        async def stop(self):
            pass

    monkeypatch.setattr('zpl_printer_emulator.app.TcpPrinterServer', FakeTcpServer)
    store = JobStore()
    app = create_app(settings=Settings(), store=store, renderer=fake_renderer)
    first = '^XA^FDFIRST^FS^XZ'
    second = '^XA\n^FDSECOND^FS^XZ'
    with TestClient(app) as client:
        client.portal.call(handlers[0], ('~HS' + first + '\n' + second).encode())
        jobs = store.latest()
        assert len(jobs) == 2
        assert {job.zpl for job in jobs} == {first, second}
        assert sorted(job.bytes_received for job in jobs) == sorted([len(first), len(second)])
