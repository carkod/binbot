FROM node:lts AS build-stage
WORKDIR /app
COPY /terminal/ /app/
RUN npm install && npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build-stage /app/dist /usr/share/nginx/html