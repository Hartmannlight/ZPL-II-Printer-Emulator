from zpl_printer_emulator.models import JobStatus
from zpl_printer_emulator.store import JobStore


def test_store_keeps_latest_jobs_only() -> None:
    store = JobStore(max_jobs=2)

    first = store.add("^XA^XZ", bytes_received=6)
    second = store.add("^XA^FO10,10^FDTwo^FS^XZ", bytes_received=24)
    third = store.add("^XA^FO10,10^FDThree^FS^XZ", bytes_received=26)

    assert store.get(first.id) is None
    assert [job.id for job in store.latest()] == [third.id, second.id]


def test_store_marks_render_result() -> None:
    store = JobStore()
    job = store.add("^XA^XZ", bytes_received=6)

    rendered = store.mark_rendered(job.id, b"png")

    assert rendered.status == JobStatus.rendered
    assert rendered.image_png == b"png"
