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
    'check_and_schedule_daily_tasks': {
        'task': 'users.tasks.check_and_schedule_daily_tasks',
        'schedule': crontab(minute=0, hour='*/1'),  # Run every 30 minutes
    },
}

# Memory optimization settings
app.conf.update(
    # Worker settings for memory efficiency
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
    worker_max_memory_per_child=400000,  # Restart worker if it uses more than 400MB (400MB in KB)
    
    # Task settings
    task_acks_late=True,  # Acknowledge tasks only after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    
    # Result backend settings (use redis or database)
    result_expires=3600,  # Results expire after 1 hour
    
    # Connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    
    # Memory optimization
    worker_disable_rate_limits=True,  # Disable rate limiting to reduce memory overhead
    task_compression='gzip',  # Compress task messages
    result_compression='gzip',  # Compress results
)


app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
