FROM node:lts as build-stage
WORKDIR /app
COPY web/package.json web/package-lock.json web/.env ./
COPY web/public public
COPY web/src src
RUN npm update npm
RUN npm install && npm install react-scripts -g
RUN npm run build

FROM tiangolo/meinheld-gunicorn-flask:python3.8
RUN apt-get update -y && apt-get install nginx -y
COPY --from=build-stage /app/ /web/build
COPY ./nginx.conf /etc/nginx/sites-enabled/default
WORKDIR /app
COPY api ./api
COPY .env Pipfile Pipfile.lock run start uwsgi.ini ./
RUN pip install --upgrade pip && pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

STOPSIGNAL SIGTERM
EXPOSE 80
