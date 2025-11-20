FROM node:lts AS build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM python:3.11
RUN apt-get update && \
    apt-get install -y libpq-dev nginx && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY api api
WORKDIR api
RUN pip install uv uvicorn fastapi \
    && uv sync --no-dev --locked --no-cache
COPY nginx.conf /etc/nginx/nginx.conf

STOPSIGNAL SIGTERM
EXPOSE 80 443 8000 5432 81
