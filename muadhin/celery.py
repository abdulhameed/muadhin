from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
# from muadhin.celery_fix import getargspec
# from SalatTracker.tasks import schedule_midnight_checks

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'muadhin.settings')

# Create a Celery instance with the name 'celery'.
app = Celery('muadhin')


app.conf.beat_schedule = {
    # 'schedule_midnight_checks': {
    #     'task': 'SalatTracker.tasks.schedule_midnight_checks',
    #     'schedule': crontab(minute='*/2'),  # Run every 2 minutes
    # },

    'check_and_schedule_daily_tasks': {
        'task': 'users.tasks.check_and_schedule_daily_tasks',
        'schedule': crontab(minute='*/2'),  # Run every 30 minutes
    },
}


# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


# BEAT_SCHEDULE = {
#     'setup_periodic_tasks': {
#         'task': 'users.tasks.setup_periodic_tasks',
#         'schedule': crontab(minute='*/30'),  # Run every 30 minutes
#         'args': (None,),  # Pass None as the 'sender' argument
#     },
# }

# celery -A muadhin worker --loglevel=info
# celery -A muadhin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler