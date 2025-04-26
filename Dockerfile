FROM python:3.10.5-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=muadhin.settings
ENV SECRET_KEY="django-insecure-build-key-just-for-collectstatic"
ENV DEBUG=False

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

# Make the entrypoint script executable
# Note: We're using the file that already exists in your project
RUN chmod +x /app/docker-entrypoint.sh

# Expose the port the app runs on
EXPOSE 8000

# Command to run when the container starts
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]
