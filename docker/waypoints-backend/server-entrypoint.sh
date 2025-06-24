#!/bin/sh

until cd /app/waypoints-project
do
	echo "Waiting for server volume..."
done

until python manage.py makemigrations
do
	echo "Waiting for migrations to process..."
done

until python manage.py migrate
do
	echo "Waiting for db to be ready..."
	sleep 2
done

python manage.py collectstatic --noinput

gunicorn -b 0.0.0.0 -p 8000 nluaba.wsgi