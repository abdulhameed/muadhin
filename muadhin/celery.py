from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
# from muadhin.celery_fix import getargspec

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muadhin.settings')

# Create a Celery instance with the name 'celery'.
app = Celery('muadhin')


app.conf.beat_schedule = {
    'schedule_midnight_checks': {
        'task': 'schedule_midnight_checks',
        'schedule': crontab(minute=0, hour=23),  # Run every day at 11:00 PM UTC
    },
}


# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()