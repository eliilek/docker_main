#!/bin/sh

until cd /app/waypoints-project
do
    echo "Waiting for server volume..."
done

python manage.py rqworker waypoints