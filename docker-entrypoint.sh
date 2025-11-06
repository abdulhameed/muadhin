#!/bin/bash
set -e

# Function to wait for a service to be available
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "Waiting for $service_name to be available at $host:$port..."
    while ! nc -z $host $port; do
        echo "  $service_name is unavailable - sleeping"
        sleep 1
    done
    echo "  $service_name is up!"
}

# Parse DATABASE_URL to extract components for health check
if [ -n "$DATABASE_URL" ]; then
    # Extract host and port from DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    DB_HOST=$(echo $DATABASE_URL | sed -e 's/.*@\([^:]*\).*/\1/')
    DB_PORT=$(echo $DATABASE_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/')
    
    # Default port if not specified
    if [ -z "$DB_PORT" ] || [ "$DB_PORT" = "$DB_HOST" ]; then
        DB_PORT=5432
    fi
    
    wait_for_service $DB_HOST $DB_PORT "PostgreSQL"
fi

# Wait for Redis if using Celery
if [ -n "$CELERY_BROKER_URL" ]; then
    # Extract Redis host and port from CELERY_BROKER_URL
    # Format: redis://host:port/db
    REDIS_HOST=$(echo $CELERY_BROKER_URL | sed -e 's/redis:\/\/\([^:]*\).*/\1/')
    REDIS_PORT=$(echo $CELERY_BROKER_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/')
    
    # Default port if not specified
    if [ -z "$REDIS_PORT" ] || [ "$REDIS_PORT" = "$REDIS_HOST" ]; then
        REDIS_PORT=6379
    fi
    
    wait_for_service $REDIS_HOST $REDIS_PORT "Redis"
fi

# Function to run Django management commands
run_django_setup() {
    echo "Running Django setup tasks..."
    
    # Apply database migrations
    echo "Applying database migrations..."
    python manage.py migrate --noinput
    
    # Always collect static files for Swagger UI to work
    echo "Preparing static files directory..."
    mkdir -p /app/staticfiles
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
    
    # Create superuser if specified (only in development)
    if [ "$DJANGO_ENV" = "development" ] && [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
        echo "Creating superuser..."
        # Try to create superuser using createsuperuser command
        python manage.py createsuperuser --noinput \
            --username="$DJANGO_SUPERUSER_USERNAME" \
            --email="$DJANGO_SUPERUSER_EMAIL" > /dev/null 2>&1 || true

        # Set password and ensure user is active
        python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muadhin.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user, created = User.objects.get_or_create(username='$DJANGO_SUPERUSER_USERNAME', defaults={'email': '$DJANGO_SUPERUSER_EMAIL'})
    user.set_password('$DJANGO_SUPERUSER_PASSWORD')
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print('Superuser configured successfully.')
except Exception as e:
    print(f'Error configuring superuser: {e}')
" > /dev/null 2>&1 || true
    fi
    
    echo "Django setup completed."
}

# Determine the service type based on the command
case "$1" in
    "celery")
        echo "Starting Celery worker..."
        exec celery -A muadhin worker --loglevel=info
        ;;
    "celery-beat")
        echo "Starting Celery beat scheduler..."
        # Wait a bit longer for the database to be ready for beat scheduler
        sleep 5
        run_django_setup
        exec celery -A muadhin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    "flower")
        echo "Starting Flower monitoring..."
        exec celery -A muadhin flower --port=5555
        ;;
    "python")
        # Handle Django development server
        if [ "$2" = "manage.py" ] && [ "$3" = "runserver" ]; then
            run_django_setup
        fi
        exec "$@"
        ;;
    "gunicorn")
        echo "Starting Gunicorn server..."
        run_django_setup
        exec "$@"
        ;;
    *)
        # For any other command, run Django setup first if it's a Django command
        if echo "$@" | grep -q "manage.py"; then
            run_django_setup
        fi
        exec "$@"
        ;;
esac