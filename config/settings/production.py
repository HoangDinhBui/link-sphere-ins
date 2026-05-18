# python
from .base import *
from datetime import timedelta
import dj_database_url
import os
from urllib.parse import urlparse
from django.core.exceptions import ImproperlyConfigured

DEBUG = False
ALLOWED_HOSTS = ['*']

# Database from Railway
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
    )
}

# Static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security: require SECRET_KEY in production
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("Missing environment variable: SECRET_KEY")

# Robust CHANNEL_LAYERS: accept full redis URL or host:port
_redis_url = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379')
_parsed = urlparse(_redis_url)
if _parsed.scheme and _parsed.scheme.startswith('redis'):
    _hosts = [(_parsed.hostname or '127.0.0.1', _parsed.port or 6379)]
else:
    # Fallback: pass raw string (channels_redis accepts URL strings too)
    _hosts = [_redis_url]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': _hosts,
        },
    },
}