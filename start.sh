#!/bin/bash
gunicorn -w 3 -b :8006 -t 90 --access-logfile /var/log/access.log --error-logfile /var/log/error.log -D api.main:app
nginx -g 'daemon off;'
