FROM node:latest as build-stage
WORKDIR /app
COPY /web/ /app/
RUN yarn install && yarn build

FROM python:3.9.5
RUN apt-get update && apt-get install -y --no-install-recommends build-essential python3-dev nginx python-setuptools
COPY --from=build-stage /app/build /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/sites-enabled/default
COPY Pipfile Pipfile.lock start ./
RUN chmod +x start
RUN rm -rf .env.local
RUN pip3 install pipenv "uvicorn[standard]" gunicorn --no-cache-dir --upgrade
RUN pipenv install --system --deploy --ignore-pipfile --clear
COPY api api
CMD ["gunicorn", "-b 0.0.0.0:8006", "-k uvicorn.workers.UvicornWorker", "--access-logfile '/var/log/nginx/web-access.log'", "--error-logfile '/var/log/nginx/web-error.log'", "-D", "api.main:app"]

STOPSIGNAL SIGTERM
EXPOSE 80 8006
