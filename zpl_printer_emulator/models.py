from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    rendering = "rendering"
    rendered = "rendered"
    failed = "failed"


class PrintJob(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    zpl: str
    bytes_received: int
    status: JobStatus = JobStatus.rendering
    image_png: bytes | None = None
    error: str | None = None


class PrintJobSummary(BaseModel):
    id: str
    created_at: datetime
    bytes_received: int
    status: JobStatus
    error: str | None = None
    has_image: bool


class TestPrintRequest(BaseModel):
    zpl: str


class PrinterSettings(BaseModel):
    label_width_mm: float = Field(gt=0, le=300)
    label_height_mm: float = Field(gt=0, le=300)
    dpmm: int = Field(ge=6, le=24)


def summarize_job(job: PrintJob) -> PrintJobSummary:
    return PrintJobSummary(
        id=job.id,
        created_at=job.created_at,
        bytes_received=job.bytes_received,
        status=job.status,
        error=job.error,
        has_image=job.image_png is not None,
    )
