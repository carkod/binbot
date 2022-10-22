# Does not work with newest ubuntu
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y --no-install-recommends build-essential python3-dev python-setuptools python3 python3-pip wget
COPY . .
RUN pip install --upgrade pip && pip install -r requirements.txt
CMD ["__init__.py"]
ENTRYPOINT ["python3"]
STOPSIGNAL SIGTERM
EXPOSE 80 443
