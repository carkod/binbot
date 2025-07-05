FROM node:lts AS build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM unit:1.33.0-python3.11
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY api api
WORKDIR api
RUN python3 -m pip install uv
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
RUN uv sync --no-cache --locked --no-dev
RUN rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY ./config.json /docker-entrypoint.d/config.json

STOPSIGNAL SIGTERM
EXPOSE 80 443 8006 5432 8007 81
