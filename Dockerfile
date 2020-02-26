FROM node:12-slim as build-stage
WORKDIR /app
COPY /web/package.json /app/
RUN yarn install
COPY /web/ /app/
RUN yarn run build

FROM tiangolo/uwsgi-nginx-flask:python3.7 AS python-dependencies
COPY requirements.txt /tmp/
COPY --from=build-stage /app/build /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY ./api/. /app/.
RUN pip install --upgrade pip
RUN pip3 install -r /tmp/requirements.txt

STOPSIGNAL SIGTERM
EXPOSE 80
