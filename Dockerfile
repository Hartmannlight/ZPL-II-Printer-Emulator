FROM python:3.13-slim-bookworm@sha256:c45a22ea000adfd9cda29364bbe7edd23001ce5cc2ad15857cfbf7766943b9ca AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS dependencies
# renovate: datasource=pypi depName=uv
ARG UV_VERSION=0.12.6
RUN python -m pip install --no-cache-dir uv==$UV_VERSION
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY zpl_printer_emulator ./zpl_printer_emulator
RUN uv sync --locked --no-dev --no-editable

FROM base AS runtime
RUN python -m pip uninstall -y setuptools wheel pip
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser
COPY --from=dependencies /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH ZPL_EMULATOR_HOST=0.0.0.0 ZPL_EMULATOR_TCP_HOST=0.0.0.0
USER 10001:10001
EXPOSE 9100 9191
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9191/health', timeout=3)"]
CMD ["python", "-m", "zpl_printer_emulator"]
