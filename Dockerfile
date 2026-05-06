FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md uv.lock /app/
COPY zpl_printer_emulator /app/zpl_printer_emulator

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN useradd --create-home --shell /bin/sh appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 9100 9191

CMD ["python", "-m", "zpl_printer_emulator"]
