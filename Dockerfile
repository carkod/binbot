FROM node:lts as build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM unit:1.33.0-python3.11
COPY --from=build-stage /app/dist /usr/share/nginx/html
ADD api api
WORKDIR api
RUN pip3 install --upgrade pip
RUN pip3 install pipenv
RUN pipenv install --system --deploy
RUN rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY ./config.json /docker-entrypoint.d/config.json
RUN ln -sf /dev/stdout /var/log/unit.log
RUN chown -R unit:unit /api/ /usr/local/bin/docker-entrypoint.sh

STOPSIGNAL SIGTERM
EXPOSE 80 8006

CMD ["alembic", "upgrade", "head"]
