#!/bin/bash

set -e

# Wait for postgres to be ready
if [ -n "$PGHOST" ]; then
    echo "Waiting for PostgreSQL to be ready..."
    while ! pg_isready -h $PGHOST -p $PGPORT -U $PGUSER; do
        sleep 1
    done
    echo "PostgreSQL is ready!"
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Prepare Celery Beat's schedule database
echo "Deleting old celerybeat schedule if it exists..."
rm -f celerybeat-schedule

# Determine what service to run based on the command
if [ "$1" = "web" ]; then
    echo "Starting Django web server..."
    exec gunicorn muadhin.wsgi:application --bind 0.0.0.0:$PORT --log-file -
elif [ "$1" = "worker" ]; then
    echo "Starting Celery worker..."
    exec celery -A muadhin worker --loglevel=info
elif [ "$1" = "beat" ]; then
    echo "Starting Celery beat..."
    exec celery -A muadhin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
    echo "Unknown service: $1"
    exit 1
fi