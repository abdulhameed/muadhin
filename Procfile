web: gunicorn muadhin.wsgi --log-file -
worker: celery -A muadhin worker --loglevel=info
beat: celery -A muadhin beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
