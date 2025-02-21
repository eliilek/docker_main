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

export CLOUDINARY_URL=$(cat /run/secrets/CLOUDINARY_URL)
export S3_ACCESS=$(cat /run/secrets/S3_ACCESS)
export S3_SECRET=$(cat /run/secrets/S3_SECRET)

python manage.py rqworker default