FROM node:lts as build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM unit:1.33.0-python3.11
RUN apt-get update --yes && apt-get install postgresql postgresql-contrib curl -y
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY api api
WORKDIR api
RUN pip3 install pipenv
RUN pipenv install --system --deploy
RUN rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY ./config.json /docker-entrypoint.d/config.json

STOPSIGNAL SIGTERM
EXPOSE 80 443 8006 5432
