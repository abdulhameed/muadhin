FROM python:3.10.5-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=muadhin.settings

# Set work directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Create directory for static files
RUN mkdir -p /app/static

# Add fake SECRET_KEY just for collectstatic
# This will be overridden by the actual SECRET_KEY in the environment
ENV SECRET_KEY="django-insecure-build-key-just-for-collectstatic"
ENV DEBUG=False

# Collect static files
RUN python manage.py collectstatic --noinput || echo "Static collection failed, but continuing the build..."


# Run as non-root user for better security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Use a script to start services
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Command to run when the container starts
ENTRYPOINT ["/app/docker-entrypoint.sh"]
