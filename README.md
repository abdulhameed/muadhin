# muadhin
A Django-based service that sends daily salah (Islamic prayer) time notifications to registered Muslim users via email, SMS, and phone calls. Utilizes Twilio for SMS and voice calls, and Celery for asynchronous task processing.


# Daily Salah Time Notification Service

A Django-based web application that provides a service to send daily salah (Islamic prayer) time notifications to registered Muslim users.

## Features

- Users can register to receive daily salah time notifications
- Notifications are delivered via email, SMS, and phone calls
- Utilizes Twilio for SMS and voice call functionalities
- Leverages Celery for asynchronous task processing and scheduling 
- Supports multiple notification channels (email, SMS, phone) for each user
- Provides an admin interface for managing user registrations and notifications

## Technologies Used

- Django web framework
- Twilio API for SMS and voice calls
- Celery for asynchronous task processing
- RabbitMQ or Redis as the message broker for Celery
- SQLite (or any other database) for storing user and notification data

## Installation and Setup

### Local Development (Traditional)

1. Clone the repository:

   ```
   git clone https://github.com/abdulhameed/daily-salah-notification.git
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

4. Set up the environment variables (e.g., Twilio credentials, database connection, etc.) in a `.env` file.

5. Run the database migrations:

   ```
   python manage.py migrate
   ```

6. Start the Django development server:

   ```
   python manage.py runserver
   ```

7. Start the Celery worker:

   ```
   celery -A muadhin worker --beat --loglevel=info
   ```

### Docker Development Setup

1. Clone the repository:

   ```
   git clone https://github.com/abdulhameed/daily-salah-notification.git
   cd muadhin
   ```

2. Build and start the development environment:

   ```
   docker-compose up --build
   ```

   This will start:
   - Django development server on `http://localhost:8080`
   - PostgreSQL database (port 5433)
   - Redis for Celery (port 6380)
   - Celery worker and beat scheduler
   - Flower monitoring on `http://localhost:5556`

3. The application will automatically:
   - Run database migrations
   - Create a superuser (admin/admin123) for development
   - Collect static files

### Docker Production Deployment

1. Create your production environment file:

   ```
   cp .env.prod.example .env.prod
   # Edit .env.prod with your production values
   ```

2. Deploy with production configuration:

   ```
   docker-compose -f docker-compose.prod.yml up -d
   ```

   This will start:
   - Django app with Gunicorn (multiple replicas)
   - Nginx reverse proxy on port 80
   - PostgreSQL database with optimized settings
   - Redis for Celery
   - Celery workers (multiple replicas)
   - Celery beat scheduler
   - Flower monitoring (protected)

3. Monitor the deployment:

   ```
   docker-compose -f docker-compose.prod.yml logs -f
   ```

### Docker Commands

```bash
# Development
docker-compose up                    # Start all services
docker-compose up --build           # Rebuild and start
docker-compose down                  # Stop all services
docker-compose logs -f web           # View Django logs

# Production
docker-compose -f docker-compose.prod.yml up -d     # Start production
docker-compose -f docker-compose.prod.yml down      # Stop production
docker-compose -f docker-compose.prod.yml logs -f   # View logs

# Utility commands
docker-compose exec web python manage.py shell      # Django shell
docker-compose exec web python manage.py migrate    # Run migrations
docker-compose exec db psql -U muadhin_user -d muadhin_db  # Database shell
```

## Usage

1. Register users through the admin interface or the provided API endpoints.
2. Scheduled tasks will automatically send daily salah time notifications to registered users via their preferred channels (email, SMS, phone).
3. Users can manage their notification preferences through the provided user interface or API.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please feel free to open a new issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
