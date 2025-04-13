from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
import pytz
from datetime import datetime, time, timedelta, timezone
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
    last_scheduled_time = models.DateTimeField(null=True, blank=True)
    midnight_utc = models.TimeField(null=True, blank=True)
    setup_completed = models.BooleanField(default=False)
        
    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        user_timezone = pytz.timezone(self.timezone)
        now = user_timezone.localize(datetime.now())
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.midnight_utc = midnight.astimezone(pytz.utc).time()
        super().save(*args, **kwargs)

    @property
    def next_midnight(self):
        user_timezone = pytz.timezone(self.timezone)
        now = user_timezone.localize(datetime.now())
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return midnight - timedelta(minutes=5)


class AuthToken(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='auth_token')
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.token


class PasswordResetToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)

    def __str__(self):
        return self.token


class SubscriptionTier(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    
    def __str__(self):
        return self.name
    

class UserPreferences(models.Model):
    NOTIFICATION_CHOICES = [
        ('email', 'Email'),
        ('call', 'Call'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    subscription_tier = models.ForeignKey(SubscriptionTier, on_delete=models.SET_NULL, null=True)
    # Daily Prayer Summary Message at Start of Day
    daily_prayer_summary_enabled = models.BooleanField(default=True)
    daily_prayer_summary_message_method = models.CharField(
        max_length=10, 
        blank=True,
        null=True, 
        choices=NOTIFICATION_CHOICES, 
        default='email'
    )

    # Notification Before Prayer Time
    pre_prayer_reminder_enabled = models.BooleanField(default=True)
    pre_prayer_reminder_method = models.CharField(
        max_length=10, 
        blank=True,
        null=True,
        choices=NOTIFICATION_CHOICES, 
        default='whatsapp'
    )
    pre_prayer_reminder_time = models.IntegerField(
        default=15, 
        help_text="Minutes before prayer time to send notification"
    )

    # Adhan Phone Call at Prayer Time
    adhan_call_enabled = models.BooleanField(default=True)
    adhan_call_method = models.CharField(
        max_length=10, 
        choices=NOTIFICATION_CHOICES, 
        default='call'
    )

    notification_methods = models.CharField(
        max_length=10,
        choices=NOTIFICATION_CHOICES,
        blank=True,
        null=True,
    )
    # Individual prayer settings
    fajr_reminder_enabled = models.BooleanField(default=True)
    zuhr_reminder_enabled = models.BooleanField(default=True)
    asr_reminder_enabled = models.BooleanField(default=True)
    maghrib_reminder_enabled = models.BooleanField(default=True)
    isha_reminder_enabled = models.BooleanField(default=True)

    fajr_adhan_call_enabled = models.BooleanField(default=True)
    zuhr_adhan_call_enabled = models.BooleanField(default=True)
    asr_adhan_call_enabled = models.BooleanField(default=True)
    maghrib_adhan_call_enabled = models.BooleanField(default=True)
    isha_adhan_call_enabled = models.BooleanField(default=True)

    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s preferences"

    def save(self, *args, **kwargs):
        if self.subscription_tier.name == "Base Plan":
            self.daily_summary_enabled = True
            self.pre_prayer_reminder_enabled = False
            self.adhan_call_enabled = False
        elif self.subscription_tier.name == "Enhanced Plan":
            self.daily_summary_enabled = True
            self.pre_prayer_reminder_enabled = True
            self.adhan_call_enabled = False
            self.pre_prayer_reminder_method = 'whatsapp'
        elif self.subscription_tier.name == "Premium Plan":
            self.daily_summary_enabled = True
            self.pre_prayer_reminder_enabled = True
            self.adhan_call_enabled = True
        super().save(*args, **kwargs)


class Location(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    

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
    is_completed = models.BooleanField(default=False)

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


class Discount(models.Model):
    code = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage discount
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        return self.is_active and (self.expires_at is None or self.expires_at > timezone.now())
    

class Subscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.ForeignKey(Discount, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def get_discounted_amount(self):
        if self.discount and self.discount.is_valid():
            return self.amount * (1 - self.discount.amount / 100)
        return self.amount
