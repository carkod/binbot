#!/bin/bash

gunicorn -w 3 -b :8006 api.main:app --daemon
nginx -g 'daemon off;'