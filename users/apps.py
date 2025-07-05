from django.apps import AppConfig
from django.db import transaction
import os


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        """
        Import signals when the app is ready.
        Also create dev admin user and fix existing users if needed.
        """
        try:
            # Import signals to register them
            import users.signals
            print("✅ User signals loaded successfully")
        except Exception as e:
            print(f"❌ Error loading user signals: {str(e)}")
        
        # Create dev admin user
        # self.create_dev_admin()

    def create_dev_admin(self):
        """Create development admin user if it doesn't exist"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            with transaction.atomic():
                if not User.objects.filter(username='admin4').exists():
                    User.objects.create_superuser(
                        username='admin4',
                        email='admin4@example1.com',
                        password='admin123456'
                    )
                    print("✅ Created admin4 user")
        except Exception as e:
            print(f"❌ Could not create admin user: {str(e)}")
