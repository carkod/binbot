FROM node:15 as build-stage
WORKDIR /app
COPY /web/package.json /app/
RUN yarn install
COPY /web/ /app/
RUN yarn run build


FROM python:3.8
RUN apt-get update && apt-get install -y --no-install-recommends build-essential python3-dev nginx
COPY --from=build-stage /app/build /var/www/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
WORKDIR app
COPY Pipfile Pipfile.lock start.sh ./
RUN chmod +x start.sh
RUN pip install --upgrade pip && pip install pipenv gunicorn
RUN pipenv install --system --deploy --ignore-pipfile
COPY api api
ENTRYPOINT ["./start.sh"]

STOPSIGNAL SIGTERM
EXPOSE 80 8006
