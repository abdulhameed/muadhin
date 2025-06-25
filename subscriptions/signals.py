from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.apps import apps

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """Automatically create a basic subscription for new users"""
    if created:
        # Import here to avoid circular imports
        from .models import SubscriptionPlan, UserSubscription
        
        try:
            basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
            UserSubscription.objects.create(
                user=instance,
                plan=basic_plan,
                status='active'
            )
            print(f"✅ Created basic subscription for new user: {instance.username}")
        except SubscriptionPlan.DoesNotExist:
            # Basic plan doesn't exist yet, will be handled by apps.py
            print(f"⚠️  Basic plan not found for user: {instance.username}")
        except Exception as e:
            print(f"❌ Failed to create subscription for user {instance.username}: {e}")
