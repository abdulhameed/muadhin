from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from subscriptions.models import UserSubscription

User = get_user_model()


@shared_task
def check_and_expire_subscriptions():
    """
    Daily task to check and expire subscriptions that have passed their end_date.
    When a subscription expires, the user's receive_notifications flag is set to False.
    """
    now = timezone.now()

    # Find all active subscriptions that have passed their end date
    expired_subscriptions = UserSubscription.objects.filter(
        status='active',
        end_date__isnull=False,  # Only check subscriptions with an end date
        end_date__lt=now
    ).select_related('user')

    count = 0
    for subscription in expired_subscriptions:
        # Update subscription status
        subscription.status = 'expired'
        subscription.save(update_fields=['status'])

        # Disable notifications for this user
        user = subscription.user
        user.receive_notifications = False
        user.save(update_fields=['receive_notifications'])

        count += 1
        print(f"✅ Expired subscription for user {user.username} (ID: {user.id})")

    if count > 0:
        print(f"✅ Total subscriptions expired: {count}")
    else:
        print("✅ No subscriptions to expire")

    return {
        "status": "success",
        "expired_count": count,
        "timestamp": now.isoformat()
    }


@shared_task
def send_expiry_warnings():
    """
    Optional task to send warnings to users whose subscriptions are about to expire.
    This runs 7 days and 1 day before expiry.
    """
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.conf import settings

    now = timezone.now()

    # Find subscriptions expiring in 7 days
    seven_days_from_now = now + timedelta(days=7)
    one_day_from_now = now + timedelta(days=1)

    # Get subscriptions expiring soon
    expiring_soon = UserSubscription.objects.filter(
        status='active',
        end_date__isnull=False,
        end_date__range=(now, seven_days_from_now)
    ).select_related('user')

    warnings_sent = 0
    for subscription in expiring_soon:
        days_remaining = (subscription.end_date - now).days

        # Only send warnings at 7 days and 1 day marks
        if days_remaining not in [7, 1]:
            continue

        user = subscription.user
        subject = f"Your {subscription.plan.name} subscription expires in {days_remaining} day{'s' if days_remaining > 1 else ''}"
        message = f"""
        Assalamu Alaikum {user.username},

        Your {subscription.plan.name} subscription will expire in {days_remaining} day{'s' if days_remaining > 1 else ''}.

        After expiry, you will no longer receive prayer time notifications.

        To continue receiving notifications, please upgrade your plan at:
        {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'your account settings'}

        JazakAllahu Khairan,
        The Muadhin Team
        """

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            warnings_sent += 1
            print(f"✅ Sent expiry warning to {user.username} ({days_remaining} days remaining)")
        except Exception as e:
            print(f"❌ Failed to send expiry warning to {user.username}: {str(e)}")

    return {
        "status": "success",
        "warnings_sent": warnings_sent,
        "timestamp": now.isoformat()
    }
