from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subscriptions'

    def ready(self):
        # Import signals
        import subscriptions.signals

        # Auto-setup subscription plans and migrate users
        self.setup_subscriptions()

    def setup_subscriptions(self):
        """Auto-setup subscription plans and migrate existing users"""
        try:
            # Check if we can access the database
            from .models import SubscriptionPlan
            SubscriptionPlan.objects.exists()
        except:
            # Database not ready, skip setup
            return
        
        self.create_plans()
        self.migrate_users()

    def create_plans(self):
        """Create the three subscription plans"""
        try:
            from .models import SubscriptionPlan
            
            plans = [
                # Basic Plan - Free
                {
                    'name': 'Basic - Salah Reminder',
                    'plan_type': 'basic',
                    'price': 0.00,
                    'description': 'Essential prayer reminders via email and SMS',
                    'sort_order': 1,
                    'daily_prayer_summary_email': True,
                    'pre_adhan_email': True,
                    'pre_adhan_sms': True,
                    'max_notifications_per_day': 10,
                },
                
                # Plus Plan - $9.99
                {
                    'name': 'Plus - Muaddhin',
                    'plan_type': 'plus',
                    'price': 9.99,
                    'description': 'Enhanced features with WhatsApp and text Adhan',
                    'sort_order': 2,
                    'daily_prayer_summary_email': True,
                    'daily_prayer_summary_whatsapp': True,
                    'pre_adhan_email': True,
                    'pre_adhan_sms': True,
                    'pre_adhan_whatsapp': True,
                    'adhan_call_text': True,
                    'max_notifications_per_day': 50,
                    'priority_support': True,
                },
                
                # Premium Plan - $19.99
                {
                    'name': 'Premium - Qiyam',
                    'plan_type': 'premium',
                    'price': 19.99,
                    'description': 'Complete experience with audio Adhan calls',
                    'sort_order': 3,
                    'daily_prayer_summary_email': True,
                    'daily_prayer_summary_whatsapp': True,
                    'pre_adhan_email': True,
                    'pre_adhan_sms': True,
                    'pre_adhan_whatsapp': True,
                    'adhan_call_text': True,
                    'adhan_call_audio': True,
                    'max_notifications_per_day': 100,
                    'priority_support': True,
                    'custom_adhan_sounds': True,
                }
            ]
            
            for plan_data in plans:
                # get_or_create prevents duplicates - only creates if plan_type doesn't exist
                plan, created = SubscriptionPlan.objects.get_or_create(
                    plan_type=plan_data['plan_type'],  # This is the unique lookup
                    defaults=plan_data  # Only used if creating new plan
                )
                if created:
                    print(f"✅ Created plan: {plan.name}")
                else:
                    print(f"⚪ Plan already exists: {plan.name}")
                    
        except Exception as e:
            print(f"❌ Error creating plans: {e}")

    def migrate_users(self):
        """Migrate existing users to basic plan"""
        try:
            from django.contrib.auth import get_user_model
            from .models import SubscriptionPlan, UserSubscription
            
            User = get_user_model()
            basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
            
            # Get users without subscriptions
            users_to_migrate = User.objects.filter(subscription__isnull=True)
            
            count = 0
            for user in users_to_migrate:
                UserSubscription.objects.create(
                    user=user,
                    plan=basic_plan,
                    status='active'
                )
                count += 1
            
            if count > 0:
                print(f"✅ Migrated {count} users to basic plan")
                
        except Exception as e:
            print(f"❌ Error migrating users: {e}")
