#!/bin/bash
python manage.py migrate

celery -A config worker -l info --concurrency=1 &

daphne -b 0.0.0.0 -p $PORT config.asgi:application
