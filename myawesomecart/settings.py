"""
Django settings for MyAwesomeCart project.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from decouple import config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _csv_config(name, default=''):
    value = config(name, default=default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _csrf_origin_from_host(host):
    if host in {'*', ''}:
        return None
    if host.startswith('.'):
        return f'https://*{host}'
    if host in {'localhost', '127.0.0.1'}:
        return f'http://{host}'
    return f'https://{host}'

# Razorpay
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='dummy_key')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='dummy_secret')

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dummy_build_key_12345')

DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = _csv_config(
    'DJANGO_ALLOWED_HOSTS',
    default='.ondigitalocean.app,my-projects-zfir.onrender.com,localhost,127.0.0.1',
)
CSRF_TRUSTED_ORIGINS = _csv_config('DJANGO_CSRF_TRUSTED_ORIGINS')
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = [
        origin for origin in (_csrf_origin_from_host(host) for host in ALLOWED_HOSTS) if origin
    ]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INSTALLED_APPS = [
    'shop.apps.ShopConfig',
    'accounts.apps.AccountsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'cloudinary_storage',
    'cloudinary',
    'rest_framework',
    'axes',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'two_factor.plugins.phonenumber',
    'django_celery_beat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'myawesomecart.urls'

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
                'shop.context_processors.global_cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'myawesomecart.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    # {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    # {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_REDIRECT_URL = 'ShopHome'
LOGOUT_REDIRECT_URL = 'ShopHome'
LOGIN_URL = 'two_factor:login'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# django-axes
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True

# Session & Cookie Security
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 900
SESSION_SAVE_EVERY_REQUEST = True
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('DJANGO_SECURE_SSL_REDIRECT', default=True, cast=bool)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Email Configuration (Resend Anymail)
INSTALLED_APPS += ["anymail"]
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
ANYMAIL = {
    "RESEND_API_KEY": config('RESEND_API_KEY', default=''),
}
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='MyAwesomeCart <send@nanda.software>')


PASSWORD_RESET_TIMEOUT = 259200

TWO_FACTOR_LOGIN_TIMEOUT = 600

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'axes': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# ─── Celery Configuration ─────────────────────────────────────
_REDIS_URL = config('REDIS_URL', default='')
CELERY_BROKER_URL = config(
    'CELERY_BROKER_URL',
    default=f'{_REDIS_URL}/0' if _REDIS_URL else 'memory://',
)
CELERY_RESULT_BACKEND = config(
    'CELERY_RESULT_BACKEND',
    default=f'{_REDIS_URL}/1' if _REDIS_URL else 'cache+memory://',
)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ─── Redis Cache Configuration ────────────────────────────────
if _REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': config('REDIS_CACHE_URL', default=f'{_REDIS_URL}/2'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# ─── Testing Overrides ────────────────────────────────────────
if 'test' in sys.argv:
    TESTING = True
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    # Use in-memory cache for tests to avoid Redis dependency
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    # Disable SSL redirection and secure cookies for testing environment
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    AXES_ENABLED = False
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    AUTHENTICATION_BACKENDS = [
        'axes.backends.AxesStandaloneBackend',
        'django.contrib.auth.backends.ModelBackend',
    ]
