from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserPreferences, PrayerMethod, PrayerOffset
from subscriptions.models import SubscriptionPlan, UserSubscription
from datetime import date, timedelta


User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile_and_subscription(sender, instance, created, **kwargs):
    """
    Signal to automatically create UserPreferences, PrayerMethod, PrayerOffset,
    and assign a basic subscription plan when a new user is created.
    """
    if created:
        try:
            # Create UserPreferences with email-only defaults (basic plan)
            UserPreferences.objects.get_or_create(
                user=instance,
                defaults={
                    'daily_prayer_summary_enabled': True,
                    'daily_prayer_summary_message_method': 'email',
                    'notification_before_prayer_enabled': True,
                    'notification_before_prayer': 'email',  # Basic plan gets email only
                    'notification_time_before_prayer': 15,
                    'adhan_call_enabled': True,
                    'adhan_call_method': 'email',  # Basic plan gets email only
                    'notification_methods': 'email',
                }
            )
            
            # Create PrayerMethod with default settings
            PrayerMethod.objects.get_or_create(
                user=instance,
                defaults={
                    'sn': 1,
                    'name': 'Muslim World League'
                }
            )
            
            # Create PrayerOffset with default values (all zeros)
            PrayerOffset.objects.get_or_create(
                user=instance,
                defaults={
                    'imsak': 0,
                    'fajr': 0,
                    'sunrise': 0,
                    'dhuhr': 0,
                    'asr': 0,
                    'maghrib': 0,
                    'sunset': 0,
                    'isha': 0,
                    'midnight': 0,
                }
            )
            
            # Assign basic subscription plan
            try:
                basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
            except SubscriptionPlan.DoesNotExist:
                # Create basic plan if it doesn't exist
                basic_plan = SubscriptionPlan.objects.create(
                    name='Basic Plan',
                    plan_type='basic',
                    price=0.00,
                    max_notifications_per_day=10,
                    features={
                        'daily_prayer_summary_email': True,
                        'pre_adhan_email': True,
                        'adhan_call_email': True,
                        'daily_prayer_summary_sms': False,
                        'daily_prayer_summary_whatsapp': False,
                        'pre_adhan_sms': False,
                        'pre_adhan_whatsapp': False,
                        'adhan_call_audio': False,
                        'adhan_call_text': False,
                    }
                )
            
            # Create user subscription with basic plan
            UserSubscription.objects.get_or_create(
                user=instance,
                defaults={
                    'plan': basic_plan,
                    'status': 'active',
                    'start_date': date.today(),
                    'end_date': None,  # Basic plan never expires
                    'is_trial': False,
                    'auto_renew': True,
                }
            )
            
            print(f"✅ Created user profile and basic subscription for: {instance.username}")
            
        except Exception as e:
            print(f"❌ Error creating user profile for {instance.username}: {str(e)}")


@receiver(post_save, sender=User)
def create_user_essentials(sender, instance, created, **kwargs):
    """
    Create essential user preferences when a new user is created.
    This prevents celery task failures due to missing UserPreferences.
    """
    if created:
        try:
            from .models import UserPreferences, PrayerMethod
            
            # Create UserPreferences with safe email-only defaults
            UserPreferences.objects.get_or_create(
                user=instance,
                defaults={
                    'daily_prayer_summary_enabled': True,
                    'daily_prayer_summary_message_method': 'email',
                    'notification_before_prayer_enabled': True,
                    'notification_before_prayer': 'email',
                    'notification_time_before_prayer': 15,
                    'adhan_call_enabled': True,
                    'adhan_call_method': 'email',
                    'notification_methods': 'email',
                }
            )
            
            # Create PrayerMethod with default
            PrayerMethod.objects.get_or_create(
                user=instance,
                defaults={
                    'sn': 1,
                    'name': 'Muslim World League'
                }
            )
            
            print(f"✅ Created user essentials for: {instance.username}")
            
        except Exception as e:
            print(f"❌ Error creating user essentials for {instance.username}: {str(e)}")
            

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save related user profile data when user is updated.
    """
    try:
        # Ensure UserPreferences exists and save
        if hasattr(instance, 'preferences'):
            instance.preferences.save()
        
        # Ensure PrayerMethod exists
        if not hasattr(instance, 'prayer_method'):
            PrayerMethod.objects.create(
                user=instance,
                sn=1,
                name='Muslim World League'
            )
            
    except Exception as e:
        print(f"❌ Error saving user profile for {instance.username}: {str(e)}")
