FROM python:3.15
RUN apt-get update && \
    apt-get install -y libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app/
WORKDIR /app
RUN uv sync --frozen --no-cache
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD /app/.venv/bin/python -m streaming.healthcheck
ENTRYPOINT ["/app/.venv/bin/python", "-m", "streaming.main"]
