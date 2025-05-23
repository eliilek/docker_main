#!/bin/sh

until cd /app/nluaba-project
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

export CLOUDINARY_URL=$(cat /run/secrets/CLOUDINARY_URL_OLD)
export S3_ACCESS=$(cat /run/secrets/S3_ACCESS)
export S3_SECRET=$(cat /run/secrets/S3_SECRET)

gunicorn -b 0.0.0.0 -p 8000 nluaba.wsgi