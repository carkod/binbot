FROM node:lts as build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM unit:python3.11
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing build-essential python3-dev libpq-dev
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY api api
WORKDIR api
RUN pip3 install --upgrade pip
RUN pip3 install pipenv --upgrade
RUN pipenv install --system --deploy --clear
RUN rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY ./config.json /docker-entrypoint.d/config.json
RUN ln -sf /dev/stdout /var/log/unit.log
RUN chown -R unit:unit /api/ /docker-entrypoint.d/config.json

STOPSIGNAL SIGTERM
EXPOSE 80 8006
