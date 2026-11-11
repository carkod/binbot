FROM python:3.15
RUN apt-get update && \
    apt-get install -y libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app/

WORKDIR /app
RUN uv sync --frozen --no-cache

STOPSIGNAL SIGTERM
EXPOSE 80 443 5432 8000

CMD ["sh", "-c", "exec .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level \"$(printf '%s' \"${LOG_LEVEL:-info}\" | tr '[:upper:]' '[:lower:]')\""]
