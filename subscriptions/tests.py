from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import SubscriptionPlan, UserSubscription
from services.subscription_service import SubscriptionService

User = get_user_model()

class SubscriptionTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.basic_plan = SubscriptionPlan.objects.create(
            name='Basic',
            plan_type='basic',
            price=0,
            daily_prayer_summary_email=True,
            pre_adhan_email=True
        )
        
        self.premium_plan = SubscriptionPlan.objects.create(
            name='Premium',
            plan_type='premium', 
            price=19.99,
            daily_prayer_summary_email=True,
            daily_prayer_summary_whatsapp=True,
            pre_adhan_email=True,
            pre_adhan_sms=True,
            pre_adhan_whatsapp=True,
            adhan_call_audio=True
        )
    
    def test_user_has_basic_plan_by_default(self):
        plan = SubscriptionService.get_user_plan(self.user)
        self.assertEqual(plan.plan_type, 'basic')
    
    def test_feature_access_basic_plan(self):
        self.assertTrue(SubscriptionService.can_user_access_feature(self.user, 'daily_prayer_summary_email'))
        self.assertFalse(SubscriptionService.can_user_access_feature(self.user, 'daily_prayer_summary_whatsapp'))
    
    def test_upgrade_to_premium(self):
        subscription = SubscriptionService.upgrade_user_plan(self.user, self.premium_plan)
        self.assertEqual(subscription.plan, self.premium_plan)
        self.assertEqual(subscription.status, 'active')
        
        # Test premium features
        self.assertTrue(SubscriptionService.can_user_access_feature(self.user, 'adhan_call_audio'))
        self.assertTrue(SubscriptionService.can_user_access_feature(self.user, 'daily_prayer_summary_whatsapp'))
    
    def test_trial_functionality(self):
        subscription = SubscriptionService.start_trial(self.user, 'premium', 7)
        self.assertEqual(subscription.status, 'trial')
        self.assertTrue(subscription.is_trial)
        self.assertEqual(subscription.days_remaining, 7)
