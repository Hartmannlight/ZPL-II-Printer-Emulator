from __future__ import annotations

import uvicorn

from .config import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "zpl_printer_emulator.app:create_app",
        host=settings.web_host,
        port=settings.web_port,
        factory=True,
    )


if __name__ == "__main__":
    main()
