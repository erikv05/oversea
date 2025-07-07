#!/bin/bash

# Replace PORT in nginx config
PORT=${PORT:-8080}
sed -i "s/listen 8080/listen $PORT/g" /etc/nginx/sites-available/default

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf