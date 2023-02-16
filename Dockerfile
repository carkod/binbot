FROM node:lts as build-stage
WORKDIR /app
COPY /web/ /app/
RUN yarn install && yarn build

FROM nginx/unit:1.28.0-python3.10
RUN apt-get update && apt-get install -y --no-install-recommends build-essential python3-dev python-setuptools
COPY --from=build-stage /app/build /usr/share/nginx/html
COPY api api
WORKDIR api
RUN pip3 install pipenv --upgrade
RUN pipenv install --system --deploy --ignore-pipfile --clear
RUN apt autoremove --purge -y && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY ./config.json /docker-entrypoint.d/config.json
RUN ln -sf /dev/stdout /var/log/unit.log
RUN chown -R unit:unit /api/ /docker-entrypoint.d/config.json

STOPSIGNAL SIGTERM
EXPOSE 80 8006
