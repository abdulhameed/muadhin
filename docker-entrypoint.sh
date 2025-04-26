#!/bin/bash

set -e

# Print environment information for debugging
echo "Running in environment: $RAILWAY_ENVIRONMENT"
echo "PORT: $PORT"

# Wait for postgres to be ready if we're in a production environment
if [ -n "$PGHOST" ]; then
    echo "Waiting for PostgreSQL to be ready..."
    # Try up to 30 times with a 2-second delay between attempts
    for i in {1..30}; do
        pg_isready -h $PGHOST -p $PGPORT -U $PGUSER && break
        echo "PostgreSQL not ready yet (attempt $i/30), waiting..."
        sleep 2
    done
    echo "PostgreSQL is ready!"
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Determine what service to run based on the command
if [ "$1" = "web" ] || [ -z "$1" ]; then
    echo "Starting Django web server on port ${PORT:-8000}..."
    exec gunicorn muadhin.wsgi:application --bind 0.0.0.0:${PORT:-8000} --log-file -
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


# #!/bin/bash

# set -e

# # Wait for postgres to be ready
# if [ -n "$PGHOST" ]; then
#     echo "Waiting for PostgreSQL to be ready..."
#     while ! pg_isready -h $PGHOST -p $PGPORT -U $PGUSER; do
#         sleep 1
#     done
#     echo "PostgreSQL is ready!"
# fi

# # Apply database migrations
# echo "Applying database migrations..."
# python manage.py migrate

# # Prepare Celery Beat's schedule database
# echo "Deleting old celerybeat schedule if it exists..."
# rm -f celerybeat-schedule

# # Determine what service to run based on the command
# if [ "$1" = "web" ]; then
#     echo "Starting Django web server..."
#     exec gunicorn muadhin.wsgi:application --bind 0.0.0.0:$PORT --log-file -
# elif [ "$1" = "worker" ]; then
#     echo "Starting Celery worker..."
#     exec celery -A muadhin worker --loglevel=info
# elif [ "$1" = "beat" ]; then
#     echo "Starting Celery beat..."
#     exec celery -A muadhin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
# else
#     echo "Unknown service: $1"
#     exit 1
# fi