#!/bin/sh

until cd /app/jake-project
do
    echo "Waiting for server volume..."
done

python manage.py rqworker jake