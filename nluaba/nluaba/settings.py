"""
Django settings for safmeds project on Heroku. For more info, see:
https://github.com/heroku/heroku-django-template

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import dj_database_url
import django_heroku

def get_secret(key, default=None):
    value = os.getenv(key, default)
    if value and os.path.isfile(value):
        with open(value) as f:
            return f.read()
    return value

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "__ek=w_1*qg2(tznbl6dk+0vr!-%h7_6nu)sqdt^qxy4k6bodn"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Application definition

INSTALLED_APPS = [
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'safmeds.apps.SafmedsConfig',
    'authtools',
    'exams',
    'realexams',
    'thesis_readiness',
    'cloudinary',
    'storages',
    'django_rq',
]

SITE_ID = 1
AUTH_USER_MODEL = 'authtools.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'safmeds.middleware.AuthRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

RQ_QUEUES = {
    'default': {
        'URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'), # If you're on Heroku
        'DEFAULT_TIMEOUT': 500,
    }
}

ROOT_URLCONF = 'nluaba.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'nluaba.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_L10N = True
USE_TZ = True

DB_SQLITE = "sqlite"
DB_POSTGRESQL = "postgresql"

DATABASES_ALL = {
    DB_SQLITE: {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR + "/db.sqlite3",
    },
    DB_POSTGRESQL: {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "NAME": os.environ.get("POSTGRES_NAME", "postgres"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": get_secret("POSTGRES_PASSWORD", "postgres"),
        "PORT": int(os.environ.get("POSTGRES_PORT", "5432")),
    },
}

DATABASES = {"default": DATABASES_ALL[os.environ.get("DJANGO_DB", DB_SQLITE)]}

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

#STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
#STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
#STATICFILES_DIRS = [
#    os.path.join(PROJECT_ROOT, 'static'),
#]

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
#STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

STORAGES = {
       "default": {
           "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
           "OPTIONS": {
               # ... your S3 options here
           }
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
       },
   }

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'nluaba'
AWS_S3_REGION_NAME = 'us-east-2'
AWS_ACCESS_KEY_ID = get_secret('S3_ACCESS')
AWS_SECRET_ACCESS_KEY = get_secret('S3_SECRET')
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False

# Activate Django-Heroku.
django_heroku.settings(locals())

LOGIN_URL = '/accounts'
LOGIN_REDIRECT_URL = '/'

CLOUDINARY_STORAGE = {
    'CLOUDINARY_URL': get_secret('C_URL'),
}