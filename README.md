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
   celery -A project_name worker --beat --loglevel=info
   ```

## Usage

1. Register users through the admin interface or the provided API endpoints.
2. Scheduled tasks will automatically send daily salah time notifications to registered users via their preferred channels (email, SMS, phone).
3. Users can manage their notification preferences through the provided user interface or API.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please feel free to open a new issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
