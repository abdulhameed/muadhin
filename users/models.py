from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth import get_user_model
import pytz
from datetime import datetime, time, timedelta
from phonenumbers import parse, is_valid_number, format_number, PhoneNumberFormat
from django.core.exceptions import ValidationError
from subscriptions.models import UserSubscription
from subscriptions.services.subscription_service import SubscriptionService


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
    timezone = models.CharField(max_length=100, default="Africa/Lagos", choices=timezone_choices)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    last_scheduled_time = models.DateTimeField(null=True, blank=True)
    midnight_utc = models.TimeField(null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    twitter_handle = models.CharField(max_length=16, blank=True, null=True)
    receive_notifications = models.BooleanField(
        default=True,
        help_text="Whether to fetch prayer times and send notifications to this user"
    )
        
    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # FIXED: Add timezone validation
        if self.timezone not in pytz.all_timezones:
            self.timezone = "Africa/Lagos"  # fallback
            
        user_timezone = pytz.timezone(self.timezone)
        now = datetime.now()
        if now.tzinfo is None:
            now = user_timezone.localize(now)
        else:
            now = now.astimezone(user_timezone)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        self.midnight_utc = midnight.astimezone(pytz.utc).time()
        super().save(*args, **kwargs)

    @property
    def next_midnight(self):
        user_timezone = pytz.timezone(self.timezone)
        now = datetime.now()
        if now.tzinfo is None:
            now = user_timezone.localize(now)
        else:
            now = now.astimezone(user_timezone)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return midnight - timedelta(minutes=5)
    
    @property
    def current_plan(self):
        """Get user's current subscription plan"""
        return SubscriptionService.get_user_plan(self)
    
    def has_feature(self, feature_name):
        """Check if user's current plan includes a specific feature"""
        return SubscriptionService.can_user_access_feature(self, feature_name)
    
    def can_send_notification(self, notification_type):
        """Check if user can send a notification (considering daily limits)"""
        try:
            subscription = self.subscription
            if subscription.is_active:
                subscription._reset_daily_usage_if_needed()
                return subscription.notifications_sent_today < subscription.plan.max_notifications_per_day
        except UserSubscription.DoesNotExist:
            # Basic plan users get limited notifications
            return True
        return False
    
    def record_notification_sent(self):
        """Record that a notification was sent"""
        try:
            subscription = self.subscription
            if subscription.is_active:
                subscription.increment_usage()
        except UserSubscription.DoesNotExist:
            pass
    
    def get_country_code(self):
        """Get user's country code for provider selection"""
        # Map common country names to codes
        country_mapping = {
            'NIGERIA': 'NG',
            'UNITED KINGDOM': 'GB', 
            'UK': 'GB',
            'GREAT BRITAIN': 'GB',
            'CANADA': 'CA',
            'AUSTRALIA': 'AU',
            'UNITED ARAB EMIRATES': 'AE',
            'UAE': 'AE',
            'SAUDI ARABIA': 'SA',
            'QATAR': 'QA',
            'UNITED STATES': 'US',
            'USA': 'US',
            'AMERICA': 'US',
        }
        
        country_upper = self.country.upper()
        return country_mapping.get(country_upper, 'GLOBAL')
    
    def get_available_plans(self):
        """Get subscription plans available for user's country"""
        from subscriptions.models import SubscriptionPlan
        country_code = self.get_country_code()
        return SubscriptionPlan.get_plans_for_country(country_code)
    
    def get_optimal_provider(self):
        """Get the best communication provider for this user's country"""
        from communications.services.provider_registry import ProviderRegistry
        country_code = self.get_country_code()
        return ProviderRegistry.get_best_provider_for_cost(country_code)
    
    @property
    def is_nigeria_user(self):
        """Check if user is from Nigeria"""
        return self.get_country_code() == 'NG'
    
    @property 
    def preferred_currency(self):
        """Get user's preferred currency based on country"""
        currency_mapping = {
            'NG': 'NGN',
            'GB': 'GBP',
            'CA': 'CAD', 
            'AU': 'AUD',
            'AE': 'AED',
            'SA': 'SAR',
            'QA': 'QAR',
        }
        return currency_mapping.get(self.get_country_code(), 'USD')


class CustomUserManager(models.Manager):
    """Custom manager with memory-efficient methods"""
    
    def get_users_needing_scheduling(self, cutoff_time):
        """Get users that need prayer time scheduling"""
        return self.filter(
            models.Q(last_scheduled_time__isnull=True) | 
            models.Q(last_scheduled_time__lt=cutoff_time)
        ).select_related('preferences').only(
            'id', 'username', 'timezone', 'last_scheduled_time', 
            'midnight_utc', 'city', 'country'
        )
    
    def bulk_update_scheduled_time(self, user_ids, scheduled_time):
        """Efficiently update last_scheduled_time for multiple users"""
        return self.filter(id__in=user_ids).update(
            last_scheduled_time=scheduled_time
        )


class AuthToken(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='auth_token')
    token = models.CharField(max_length=255, unique=True)  # Added unique=True
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.username}"


class UserPreferences(models.Model):
    NOTIFICATION_METHODS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='preferences')
    
    # Daily Prayer Summary
    daily_prayer_summary_enabled = models.BooleanField(default=True)
    daily_prayer_summary_message_method = models.CharField(
        max_length=10,
        choices=NOTIFICATION_METHODS,
        default='email'
    )

    # Notification Before Prayer Time
    notification_before_prayer_enabled = models.BooleanField(default=True)
    notification_before_prayer = models.CharField(
        max_length=10,
        choices=NOTIFICATION_METHODS,
        default='sms'
    )
    notification_time_before_prayer = models.IntegerField(
        default=15, 
        blank=True, 
        null=True, 
        help_text="Number of minutes before prayer time to send notification"
    )

    # Adhan Phone Call at Prayer Time
    ADHAN_METHODS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('call', 'Phone Call'),
        ('text', 'Text Message'),
    ]
    adhan_call_enabled = models.BooleanField(default=True)
    adhan_call_method = models.CharField(
        max_length=10,
        choices=ADHAN_METHODS,
        default='email'
    )

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
    utc_time_for_1159 = models.TimeField(null=True, blank=True)
    show_last_third = models.BooleanField(default=False)
    # git add . && git commit -m "Add user preferences model with timezone handling and validation"

    def save(self, *args, **kwargs):
        # Calculate and store UTC time for 11:59 AM in the user's timezone
        try:
            user_timezone = pytz.timezone(self.user.timezone)
            local_time_1159 = datetime.combine(datetime.today(), time(11, 59))
            utc_time_1159 = user_timezone.localize(local_time_1159).astimezone(pytz.utc).time()
            self.utc_time_for_1159 = utc_time_1159
        except Exception:
            # Fallback if timezone calculation fails
            self.utc_time_for_1159 = time(9, 59)  # Approximately 11:59 Lagos time in UTC
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username}'s preferences"
    
    def clean(self):
        """Validate preferences against subscription plan"""
        super().clean()
        
        # Validate daily prayer summary method
        if not SubscriptionService.validate_notification_preference(
            self.user, 'daily_prayer_summary', self.daily_prayer_summary_message_method
        ):
            raise ValidationError({
                'daily_prayer_summary_message_method': 
                f'Your current plan does not include {self.get_daily_prayer_summary_message_method_display()} for daily summaries. Please upgrade your plan.'
            })
        
        # Validate pre-adhan notification method
        if not SubscriptionService.validate_notification_preference(
            self.user, 'pre_adhan', self.notification_before_prayer
        ):
            raise ValidationError({
                'notification_before_prayer': 
                f'Your current plan does not include {self.get_notification_before_prayer_display()} for pre-adhan notifications. Please upgrade your plan.'
            })
        
        # Validate adhan call method
        if not SubscriptionService.validate_notification_preference(
            self.user, 'adhan_call', self.adhan_call_method
        ):
            raise ValidationError({
                'adhan_call_method': 
                f'Your current plan does not include {self.get_adhan_call_method_display()} for adhan calls. Please upgrade your plan.'
            })


class Location(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='location')
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s location"


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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='prayer_method')
    sn = models.IntegerField(choices=METHOD_CHOICES, default=1)
    name = models.CharField(max_length=50, default='Muslim World League')

    @property
    def method_name(self):
        # FIXED: Use self.sn instead of self.id
        return dict(self.METHOD_CHOICES).get(self.sn, "Unknown Method")

    def __str__(self):
        return f"{self.user.username}'s prayer method: {self.method_name}"


class PrayerOffset(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='prayer_offset')
    imsak = models.IntegerField(null=True, blank=True, default=0)
    fajr = models.IntegerField(null=True, blank=True, default=0)
    sunrise = models.IntegerField(null=True, blank=True, default=0)
    dhuhr = models.IntegerField(null=True, blank=True, default=0)
    asr = models.IntegerField(null=True, blank=True, default=0)
    maghrib = models.IntegerField(null=True, blank=True, default=0)
    sunset = models.IntegerField(null=True, blank=True, default=0)
    isha = models.IntegerField(null=True, blank=True, default=0)
    midnight = models.IntegerField(null=True, blank=True, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s prayer offsets"
