FROM node:12-slim as build-stage
WORKDIR /app
COPY /web/package.json /app/
RUN yarn install
COPY /web/ /app/
RUN yarn run build

FROM python:3.6-slim
RUN apt-get clean \
    && apt-get -y update
RUN apt-get -y install nginx \
    && apt-get -y install python3-dev \
    && apt-get -y install build-essential
WORKDIR /app
COPY --from=build-stage /app/ /app/web/build
COPY ./nginx.conf /etc/nginx/sites-enabled/default
ADD . .
RUN pip install --upgrade pip
RUN pip3 install -r requirements.txt
RUN chmod +x ./start

STOPSIGNAL SIGTERM
EXPOSE 80

CMD ["./start"]
