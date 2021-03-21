FROM python:3.8
RUN apt-get update && apt-get install -y --no-install-recommends build-essential python3-dev nginx wheel python-setuptools python-wheel
COPY web/build /var/www/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY Pipfile Pipfile.lock start ./
RUN chmod +x start
RUN pip install --upgrade pip && pip install pipenv gunicorn
RUN pipenv install --system --deploy --ignore-pipfile
COPY api api
CMD ["./start"]

STOPSIGNAL SIGTERM
EXPOSE 80
