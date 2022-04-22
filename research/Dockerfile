# Does not work with newest ubuntu
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y --no-install-recommends build-essential python3-dev python-setuptools python3 python3-pip wget
# Install ta-lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xvf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make \
    && make install
COPY . .
RUN pip install --upgrade pip && pip install -r requirements.txt
CMD ["__init__.py"]
ENTRYPOINT ["python3"]
STOPSIGNAL SIGTERM
EXPOSE 80 443
