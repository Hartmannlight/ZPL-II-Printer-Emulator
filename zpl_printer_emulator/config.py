from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    web_host: str = "127.0.0.1"
    web_port: int = 9191
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 9100
    label_width_in: float = 1.9685
    label_height_in: float = 0.9843
    dpmm: int = 8
    labelary_url: str = "https://api.labelary.com"
    max_jobs: int = 50


def load_settings() -> Settings:
    return Settings(
        web_host=os.getenv("ZPL_EMULATOR_HOST", "127.0.0.1"),
        web_port=_env_int("ZPL_EMULATOR_WEB_PORT", 9191),
        tcp_host=os.getenv("ZPL_EMULATOR_TCP_HOST", "127.0.0.1"),
        tcp_port=_env_int("ZPL_EMULATOR_TCP_PORT", 9100),
        label_width_in=_env_float("ZPL_EMULATOR_LABEL_WIDTH_IN", 1.9685),
        label_height_in=_env_float("ZPL_EMULATOR_LABEL_HEIGHT_IN", 0.9843),
        dpmm=_env_int("ZPL_EMULATOR_DPMM", 8),
        labelary_url=os.getenv("ZPL_EMULATOR_LABELARY_URL", "https://api.labelary.com"),
        max_jobs=_env_int("ZPL_EMULATOR_MAX_JOBS", 50),
    )


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    return float(raw)
