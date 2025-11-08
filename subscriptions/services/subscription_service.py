from django.core.exceptions import ValidationError
from subscriptions.models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from django.utils import timezone
from datetime import timedelta


class SubscriptionService:
    """Service class to handle subscription-related business logic"""
    
    @staticmethod
    def get_user_plan(user):
        """Get user's current subscription plan"""
        try:
            subscription = user.subscription
            if subscription.is_active:
                return subscription.plan
        except UserSubscription.DoesNotExist:
            pass

        # Return basic plan as default, or None if it doesn't exist
        try:
            return SubscriptionPlan.objects.get(plan_type='basic')
        except SubscriptionPlan.DoesNotExist:
            # Return the first available plan or None
            return SubscriptionPlan.objects.filter(is_active=True).first()
    
    @staticmethod
    def can_user_access_feature(user, feature_name):
        """Check if user can access a specific feature"""
        try:
            subscription = user.subscription
            if not subscription.is_active:
                # Fall back to basic plan features
                try:
                    basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
                    return getattr(basic_plan, feature_name, False)
                except SubscriptionPlan.DoesNotExist:
                    # No basic plan exists, deny access to premium features
                    return False

            return subscription.can_use_feature(feature_name)
        except UserSubscription.DoesNotExist:
            # User has no subscription, check basic plan
            try:
                basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
                return getattr(basic_plan, feature_name, False)
            except SubscriptionPlan.DoesNotExist:
                # No basic plan exists, deny access to premium features
                return False
    
    @staticmethod
    def upgrade_user_plan(user, new_plan, payment_method=None):
        """Upgrade user to a new plan"""
        try:
            subscription = user.subscription
            old_plan = subscription.plan
        except UserSubscription.DoesNotExist:
            # Create new subscription
            subscription = UserSubscription.objects.create(user=user, plan=new_plan)
            old_plan = None
        
        # Record the change
        SubscriptionHistory.objects.create(
            user=user,
            from_plan=old_plan,
            to_plan=new_plan,
            reason='upgrade'
        )
        
        # Update subscription
        subscription.plan = new_plan
        subscription.status = 'active'
        subscription.start_date = timezone.now()

        # Set end date based on billing cycle
        if new_plan.billing_cycle == 'monthly':
            subscription.end_date = timezone.now() + timedelta(days=30)
        elif new_plan.billing_cycle == 'yearly':
            subscription.end_date = timezone.now() + timedelta(days=365)
        else:  # lifetime
            subscription.end_date = None

        subscription.save()

        # Re-enable notifications if they were disabled due to expiry
        if not user.receive_notifications:
            user.receive_notifications = True
            user.save(update_fields=['receive_notifications'])

        return subscription
    
    @staticmethod
    def start_trial(user, plan_type='premium', trial_days=7):
        """Start a trial for the user"""
        try:
            subscription = user.subscription
            if subscription.status == 'trial':
                raise ValidationError("User is already on trial")
        except UserSubscription.DoesNotExist:
            subscription = None

        try:
            premium_plan = SubscriptionPlan.objects.get(plan_type=plan_type)
        except SubscriptionPlan.DoesNotExist:
            raise ValidationError(f"No {plan_type} plan available. Please create a subscription plan first.")

        if subscription:
            subscription.plan = premium_plan
            subscription.start_trial(trial_days)
        else:
            subscription = UserSubscription.objects.create(
                user=user,
                plan=premium_plan,
                status='trial',
                trial_end_date=timezone.now() + timedelta(days=trial_days)
            )

        return subscription
    
    @staticmethod
    def validate_notification_preference(user, notification_type, method):
        """Validate if user can set a specific notification method"""
        feature_map = {
            'daily_prayer_summary': {
                'email': 'daily_prayer_summary_email',
                'whatsapp': 'daily_prayer_summary_whatsapp',
            },
            'pre_adhan': {
                'email': 'pre_adhan_email',
                'sms': 'pre_adhan_sms',
                'whatsapp': 'pre_adhan_whatsapp',
            },
            'adhan_call': {
                'call': 'adhan_call_audio',
                'text': 'adhan_call_text',
            }
        }
        
        if notification_type in feature_map and method in feature_map[notification_type]:
            feature_name = feature_map[notification_type][method]
            return SubscriptionService.can_user_access_feature(user, feature_name)
        
        return False
