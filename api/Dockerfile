FROM python:3.11
RUN apt-get update && \
    apt-get install -y libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /api/

WORKDIR /api
RUN uv sync --frozen --no-cache

STOPSIGNAL SIGTERM
EXPOSE 80 443 5432 8000

CMD [".venv/bin/fastapi", "run", "main.py", "--port", "8000", "--workers", "8"]
