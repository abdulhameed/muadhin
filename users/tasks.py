from celery import Celery
from celery.schedules import crontab
from .models import UserProfile, CustomUser  # Import your user profile model
from SalatTracker.utils import fetch_and_save_prayer_times


app = Celery('users')

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    user_profiles = UserProfile.objects.all()  # Query all user profiles with timezones
    
    for user_profile in user_profiles:
        user_timezone = user_profile.timezone
        midnight = CustomUser.next_midnight(user_timezone)
        sender.add_periodic_task(
            crontab(
                minute=midnight.minute,
                hour=midnight.hour,
                day_of_month=midnight.day,
                month_of_year=midnight.month,
            ),
            fetch_and_save_prayer_times.s(user_profile.id),  # Pass user-specific data to the task
        )
