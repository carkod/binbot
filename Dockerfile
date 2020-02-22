FROM ubuntu:focal AS python-dependencies
RUN apt update && \
    apt install -y python3-pip python3-dev build-essential
COPY . /var/www/.
RUN pip3 install --user --requirement /var/www/requirements.txt

FROM ubuntu:focal
RUN apt update -y && \
    apt install -y python3-pip python3-dev build-essential apache2
RUN a2enmod rewrite && \
    a2enmod proxy && a2enmod proxy_http && a2enmod proxy_balancer && a2enmod rewrite && a2enmod lbmethod_byrequests

COPY --from=python-dependencies /root/.local/lib/python3.8/site-packages/ /root/.local/lib/python3.8/site-packages/
COPY --from=python-dependencies /var/www /var/www


# Manually set up the apache environment variables
ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2
ENV APACHE_LOCK_DIR /var/lock/apache2
ENV APACHE_PID_FILE /var/run/apache2.pid

# Expose apache.
EXPOSE 80

# Update the default apache site with the config we created.
COPY apache-config.conf /etc/apache2/sites-enabled/000-default.conf
RUN service apache2 restart


CMD ["python3", "/var/www/api/run.py"]
# ENTRYPOINT ["httpd" "-D", "FOREGROUND"]