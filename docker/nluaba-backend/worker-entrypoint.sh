#!/bin/sh

until cd /app/nluaba-project
do
    echo "Waiting for server volume..."
done

python manage.py rqworker nluaba