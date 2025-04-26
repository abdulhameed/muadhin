#!/bin/bash

set -e

# Print environment for debugging
echo "APPLICATION STARTING..."
echo "DATABASE_URL: ${DATABASE_URL:-Not set}"
echo "PGHOST: ${PGHOST:-Not set}"
echo "PGPORT: ${PGPORT:-Not set}"
echo "PGDATABASE: ${PGDATABASE:-Not set}"
echo "PGUSER: ${PGUSER:-Not set}"
echo "RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT:-Not set}"
echo "PORT: ${PORT:-Not set}"

# Create a simplified database config for the healthcheck
echo "Creating simple Django app for database testing..."
mkdir -p /tmp/dbtest
cat > /tmp/dbtest/test_db.py << EOF
import os
import sys
import psycopg2
import time

# Try different connection methods
def test_connections():
    # Method 1: Direct psycopg2 with DATABASE_URL
    if os.getenv('DATABASE_URL'):
        print("Testing connection with DATABASE_URL...")
        try:
            import dj_database_url
            config = dj_database_url.config()
            conn = psycopg2.connect(
                dbname=config['NAME'],
                user=config['USER'],
                password=config['PASSWORD'],
                host=config['HOST'],
                port=config['PORT']
            )
            conn.close()
            print("✅ DATABASE_URL connection successful!")
            return True
        except Exception as e:
            print(f"❌ DATABASE_URL connection failed: {e}")
    
    # Method 2: Direct psycopg2 with individual vars
    if os.getenv('PGHOST'):
        print("Testing connection with PGHOST, PGUSER, etc...")
        try:
            conn = psycopg2.connect(
                dbname=os.getenv('PGDATABASE'),
                user=os.getenv('PGUSER'),
                password=os.getenv('PGPASSWORD'),
                host=os.getenv('PGHOST'),
                port=os.getenv('PGPORT')
            )
            conn.close()
            print("✅ PG* variables connection successful!")
            return True
        except Exception as e:
            print(f"❌ PG* variables connection failed: {e}")
    
    return False

# Try to connect multiple times
for i in range(5):
    print(f"\nConnection attempt {i+1}/5...")
    if test_connections():
        sys.exit(0)
    time.sleep(3)

print("All connection attempts failed!")
sys.exit(1)
EOF

# Test database connection
echo "Testing database connection..."
python /tmp/dbtest/test_db.py

# Wait for postgres if needed
if [ -n "$PGHOST" ]; then
    echo "Waiting for PostgreSQL to be ready..."
    # Try up to 30 times with a 2-second delay
    for i in {1..30}; do
        if pg_isready -h "$PGHOST" -p "${PGPORT:-5432}" -U "$PGUSER"; then
            echo "PostgreSQL is ready!"
            break
        fi
        echo "PostgreSQL not ready yet (attempt $i/30), waiting..."
        sleep 2
        if [ $i -eq 30 ]; then
            echo "PostgreSQL did not become ready in time!"
        fi
    done
fi

# Skip migrations if an env var is set (for testing purposes)
if [ "${SKIP_MIGRATIONS:-no}" != "yes" ]; then
    # Apply database migrations
    echo "Applying database migrations..."
    python manage.py migrate || echo "Migrations failed but continuing..."
else
    echo "Skipping migrations as requested."
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Static collection failed but continuing..."

# Create a simple health check endpoint without DB dependency
echo "Creating health check endpoint..."
mkdir -p /app/muadhin/simple_health
cat > /app/muadhin/simple_health/__init__.py << EOF
# Simple health check package
EOF

cat > /app/muadhin/simple_health/views.py << EOF
from django.http import JsonResponse

def simple_health(request):
    return JsonResponse({"status": "ok"})
EOF

# Add health check URL
if ! grep -q "simple_health" /app/muadhin/urls.py; then
    echo "Adding health check URL pattern..."
    sed -i '/urlpatterns = \[/a \    path("simple-health/", include("muadhin.simple_health.urls")),\n    path("health/", include("muadhin.simple_health.urls")),\n    path("ping/", include("muadhin.simple_health.urls")),\n' /app/muadhin/urls.py || echo "Couldn't add health check URL pattern"
    
    # Make sure include is imported
    sed -i '1s/^/from django.urls import include\n/' /app/muadhin/urls.py || echo "Couldn't add include import"
    
    # Create urls.py for simple_health
    mkdir -p /app/muadhin/simple_health
    cat > /app/muadhin/simple_health/urls.py << EOF
from django.urls import path
from . import views

urlpatterns = [
    path('', views.simple_health, name='simple_health'),
]
EOF
fi

# Determine what service to run based on the command
if [ "$1" = "web" ] || [ -z "$1" ]; then
    echo "Starting Django web server on port ${PORT:-8000}..."
    exec gunicorn muadhin.wsgi:application --bind 0.0.0.0:${PORT:-8000} --log-file - --access-logfile - --error-logfile - --capture-output
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