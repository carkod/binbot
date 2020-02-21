FROM ubuntu:bionic AS python-dependencies
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
ADD . /app
RUN pip3 install --user --requirement /app/requirements.txt

FROM ubuntu:bionic
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
COPY --from=python-dependencies /root/.local/lib/python3.6/site-packages/ /root/.local/lib/python3.6/site-packages/
COPY --from=python-dependencies app/ app/

ENTRYPOINT ["python3"]
CMD ["app/api/run.py"]