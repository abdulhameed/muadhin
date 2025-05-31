from django.db import models
# from django.contrib.auth.models import User
from django.contrib.auth import get_user_model


User = get_user_model()

class DailyPrayer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='daily_prayers')
    prayer_date = models.DateField(null=True, blank=True)
    weekday_name = models.CharField(max_length=20, null=True, blank=True)
    is_email_notified = models.BooleanField(default=False)
    is_sms_notified = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'prayer_date']  # Prevent duplicate daily prayers

    def __str__(self):
        return f"{self.user.username if self.user else 'No User'}'s daily prayer on {self.prayer_date}"


class PrayerTime(models.Model):
    daily_prayer = models.ForeignKey(DailyPrayer, on_delete=models.CASCADE, null=True, blank=True, related_name='prayer_times')
    prayer_name = models.CharField(max_length=50)
    prayer_time = models.TimeField(null=True, blank=True)
    is_sms_notified = models.BooleanField(default=False)
    is_phonecall_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['daily_prayer', 'prayer_name']  # Prevent duplicate prayers for same day

    def __str__(self):
        username = self.daily_prayer.user.username if self.daily_prayer and self.daily_prayer.user else 'No User'
        return f"{username}'s {self.prayer_name} prayer at {self.prayer_time}"

    def get_prayer_time(self, prayer_name):
        return self.prayer_time if self.prayer_name == prayer_name else None    
    