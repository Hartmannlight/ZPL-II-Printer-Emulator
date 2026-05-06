from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, load_settings
from .labelary import render_zpl_to_png
from .models import PrintJobSummary, TestPrintRequest, summarize_job
from .store import JobStore
from .tcp_server import TcpPrinterServer

Renderer = Callable[[str, Settings], bytes]


def create_app(
    *,
    settings: Settings | None = None,
    store: JobStore | None = None,
    renderer: Renderer = render_zpl_to_png,
    start_tcp: bool = True,
) -> FastAPI:
    active_settings = settings or load_settings()
    active_store = store or JobStore(max_jobs=active_settings.max_jobs)
    tcp_server: TcpPrinterServer | None = None

    async def process_zpl(zpl: str, *, bytes_received: int) -> str:
        job = active_store.add(zpl, bytes_received=bytes_received)

        async def render_job() -> None:
            try:
                image = await asyncio.to_thread(renderer, zpl, active_settings)
            except Exception as exc:  # noqa: BLE001 - surface renderer failures in the UI.
                active_store.mark_failed(job.id, str(exc))
                return
            active_store.mark_rendered(job.id, image)

        asyncio.create_task(render_job())
        return job.id

    async def handle_tcp_payload(payload: bytes) -> None:
        zpl = payload.decode("utf-8", errors="replace")
        await process_zpl(zpl, bytes_received=len(payload))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        nonlocal tcp_server
        if start_tcp:
            tcp_server = TcpPrinterServer(
                active_settings.tcp_host,
                active_settings.tcp_port,
                handle_tcp_payload,
            )
            await tcp_server.start()
        try:
            yield
        finally:
            if tcp_server is not None:
                await tcp_server.stop()

    app = FastAPI(title="ZPL-II Printer Emulator", version="0.1.0", lifespan=lifespan)
    app.state.settings = active_settings
    app.state.store = active_store

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/jobs", response_model=list[PrintJobSummary])
    def list_jobs(limit: int = 20) -> list[PrintJobSummary]:
        return [summarize_job(job) for job in active_store.latest(limit=limit)]

    @app.get("/api/jobs/{job_id}", response_model=PrintJobSummary)
    def get_job(job_id: str) -> PrintJobSummary:
        job = active_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return summarize_job(job)

    @app.get("/api/jobs/{job_id}/image")
    def get_job_image(job_id: str) -> Response:
        job = active_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.image_png is None:
            raise HTTPException(status_code=404, detail="Image not available")
        return Response(content=job.image_png, media_type="image/png")

    @app.post("/api/test-print", response_model=PrintJobSummary)
    async def test_print(payload: TestPrintRequest) -> PrintJobSummary:
        job_id = await process_zpl(payload.zpl, bytes_received=len(payload.zpl.encode("utf-8")))
        job = active_store.get(job_id)
        if job is None:
            raise HTTPException(status_code=500, detail="Job creation failed")
        return summarize_job(job)

    return app
