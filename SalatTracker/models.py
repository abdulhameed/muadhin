from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model


User = get_user_model()

# class PrayerTime(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     prayer_name = models.CharField(max_length=50)  # Name of the prayer (e.g., Fajr, Dhuhr, Asr, Maghrib, Isha)
#     prayer_time = models.TimeField(null=True, blank=True)  # Actual time of the prayer
#     prayer_date = models.DateField(null=True, blank=True)  # Date for which the prayer time is applicable
#     weekday_name = models.CharField(max_length=20, null=True, blank=True)  # Name of the weekday
#     is_email_notified = models.BooleanField(default=False)  # Flag to track if a reminder has been sent
#     is_sms_notified = models.BooleanField(default=False)  # Flag to track if a reminder has been sent
#     is_phonecall_notified = models.BooleanField(default=False)  # Flag to track if a reminder has been sent
#     created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the record was created
#     updated_at = models.DateTimeField(auto_now=True)  # Timestamp when the record was last updated

#     def __str__(self):
#         return f"{self.user.username}'s {self.prayer_name} prayer at {self.prayer_time}"
    
#     def get_prayer_time(self, prayer_name):
#         return self.prayer_time if self.prayer_name == prayer_name else None


class DailyPrayer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prayer_date = models.DateField(null=True, blank=True)  # Date for which the prayer times are applicable
    weekday_name = models.CharField(max_length=20, null=True, blank=True)  # Name of the weekday
    is_email_notified = models.BooleanField(default=False)  # Flag to track if a reminder has been sent

    def __str__(self):
        return f"{self.user.username}'s daily prayer on {self.prayer_date}"


class PrayerTime(models.Model):
    daily_prayer = models.ForeignKey(DailyPrayer, on_delete=models.CASCADE)
    prayer_name = models.CharField(max_length=50)  # Name of the prayer (e.g., Fajr, Dhuhr, Asr, Maghrib, Isha)
    prayer_time = models.TimeField(null=True, blank=True)  # Actual time of the prayer
    is_sms_notified = models.BooleanField(default=False)  # Flag to track if a reminder has been sent
    is_phonecall_notified = models.BooleanField(default=False)  # Flag to track if a reminder has been sent
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the record was created
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp when the record was last updated

    def __str__(self):
        return f"{self.daily_prayer.user.username}'s {self.prayer_name} prayer at {self.prayer_time}"

    def get_prayer_time(self, prayer_name):
        return self.prayer_time if self.prayer_name == prayer_name else None
    