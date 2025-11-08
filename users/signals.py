from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import UserPreferences, PrayerMethod, PrayerOffset
from subscriptions.models import SubscriptionPlan, UserSubscription


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
            # Try to get a free global basic plan first, then any basic plan, or create one
            try:
                # First, try to get FREE global basic plan
                basic_plan = SubscriptionPlan.objects.filter(
                    plan_type='basic',
                    country='GLOBAL',
                    price=0.00,
                    is_active=True
                ).first()

                if not basic_plan:
                    # If no free global plan, get the cheapest active basic plan
                    basic_plan = SubscriptionPlan.objects.filter(
                        plan_type='basic',
                        is_active=True
                    ).order_by('price').first()

                if not basic_plan:
                    raise SubscriptionPlan.DoesNotExist

            except SubscriptionPlan.DoesNotExist:
                # Create FREE global basic plan if it doesn't exist
                basic_plan = SubscriptionPlan.objects.create(
                    name='Basic - Salah Reminder (Free)',
                    plan_type='basic',
                    country='GLOBAL',
                    currency='USD',
                    price=0.00,
                    billing_cycle='monthly',
                    description='Free basic prayer reminders via email. Perfect for getting started.',
                    is_active=True,
                    sort_order=0,
                    daily_prayer_summary_email=True,
                    pre_adhan_email=True,
                    adhan_call_text=False,
                    max_notifications_per_day=15,
                    priority_support=False,
                    custom_adhan_sounds=False,
                )
            
            # Create user subscription with basic plan
            # New users get 1 month free trial, then subscription expires
            UserSubscription.objects.get_or_create(
                user=instance,
                defaults={
                    'plan': basic_plan,
                    'status': 'active',
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=30),  # 1-month free trial for new users
                }
            )
            
            print(f"✅ Created user profile and basic subscription for: {instance.username}")
            
        except Exception as e:
            print(f"❌ Error creating user profile for {instance.username}: {str(e)}")


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
