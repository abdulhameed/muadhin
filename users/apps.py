from django.apps import AppConfig
from django.db import transaction


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        self.create_dev_admin()

    def create_dev_admin(self):
        try:
            from django.contrib.auth.models import User
            with transaction.atomic():
                if not User.objects.filter(username='admin4').exists():
                    User.objects.create_superuser(
                        username='admin4',
                        email='admin4@example1.com',
                        password='admin123456'
                    )
        except Exception:
            # Database might not be ready yet
            pass
