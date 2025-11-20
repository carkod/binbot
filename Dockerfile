FROM node:lts AS build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM python:3.11
RUN apt-get update && \
    apt-get install -y libpq-dev nginx && \
    rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY api /api/
COPY nginx.conf /etc/nginx/

WORKDIR /api
RUN uv sync --frozen --no-cache

STOPSIGNAL SIGTERM
EXPOSE 80 443 5432 8000

CMD [".venv/bin/fastapi", "run", "main.py", "--port", "8000", "--workers", "4"]
