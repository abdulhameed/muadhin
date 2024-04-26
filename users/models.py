from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
import pytz
from datetime import datetime, time, timedelta
from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat


# Get a list of all valid time zones
all_timezones = pytz.all_timezones

# Create a list of tuples in the format ('timezone', 'timezone')
timezone_choices = [(tz, tz) for tz in all_timezones]

# user = get_user_model()

class CustomUser(AbstractUser):
    sex = models.CharField(max_length=10, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, default="ABUJA")
    country = models.CharField(max_length=100, default="NIGERIA")
    timezone = models.CharField(max_length=100, default="Africa/Lagos")
    phone_number = models.CharField(max_length=20, null=True, blank=True)
        
    def __str__(self):
        return self.username
    
    @property
    def next_midnight(self):
        now = datetime.now(pytz.timezone(self.timezone))
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return midnight
    

class UserPreferences(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    # Daily Prayer Message at Start of Day
    daily_prayer_message_method = models.CharField(max_length=10, choices=[('email', 'Email'), ('sms', 'SMS')], default='email')

    # Notification Before Prayer Time
    notification_before_prayer = models.CharField(max_length=10, choices=[('email', 'Email'), ('sms', 'SMS')], default='sms')
    notification_time_before_prayer = models.IntegerField(default=15, help_text="Number of minutes before prayer time to send notification")

    # Adhan Phone Call at Prayer Time
    adhan_call_method = models.CharField(max_length=10, choices=[('email', 'Email'), ('sms', 'SMS'), ('call', 'Phone Call')], default='call')

    NOTIFICATION_CHOICES = [
        ('email', 'Email'),
        ('call', 'Call'),
        ('sms', 'SMS'),
    ]
    notification_methods = models.CharField(
        max_length=10,
        choices=NOTIFICATION_CHOICES,
        blank=True,
        null=True,
    )
    # notification_time = models.TimeField()
    utc_time_for_1159 = models.TimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Calculate and store UTC time for 11:59 AM in the user's timezone
        user_timezone = pytz.timezone(self.user.timezone)
        local_time_1159 = datetime.combine(datetime.today(), time(11, 59))
        utc_time_1159 = user_timezone.localize(local_time_1159).astimezone(pytz.utc).time()
        self.utc_time_for_1159 = utc_time_1159
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username


class Location(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    

class PrayerMethod(models.Model):
    METHOD_CHOICES = (
        (1, 'Muslim World League'),
        (2, 'Islamic Society of North America'),
        (3, 'Egyptian General Authority of Survey'),
        (4, 'Umm Al-Qura University, Makkah'),
        (5, 'University of Islamic Sciences, Karachi'),
        (6, 'Institute of Geophysics, University of Tehran'),
        (7, 'Shia Ithna-Ashari, Leva Institute, Qum'),
        (8, 'Gulf Region'),
        (9, 'Kuwait'),
        (10, 'Qatar'),
        (11, 'Majlis Ugama Islam Singapura, Singapore'),
        (12, 'Union Organization Islamic de France'),
        (13, 'Diyanet İşleri Başkanlığı, Turkey'),
        (14, 'Spiritual Administration of Muslims of Russia'),
        (15, 'Moonsighting Committee'),
        (16, 'Dubai, UAE - Batoul Apps Team'),
    )
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    sn = models.IntegerField(choices=METHOD_CHOICES, default=1)
    name = models.CharField(max_length=50, default='Muslim World League')

    @property
    def method_name(self):
        return dict(self.METHOD_CHOICES).get(self.id, "Unknown Method")


class PrayerOffset(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    imsak = models.IntegerField(null=True, blank=True)
    fajr = models.IntegerField(null=True, blank=True)
    sunrise = models.IntegerField(null=True, blank=True)
    dhuhr = models.IntegerField(null=True, blank=True)
    asr = models.IntegerField(null=True, blank=True)
    maghrib = models.IntegerField(null=True, blank=True)
    sunset = models.IntegerField(null=True, blank=True)
    isha = models.IntegerField(null=True, blank=True)
    midnight = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
