from django.apps import AppConfig
from django.db import transaction
import os


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        """
        Import signals when the app is ready.
        Also create dev admin user and fix existing users if needed.
        """
        try:
            # Import signals to register them
            import users.signals
            print("✅ User signals loaded successfully")
        except Exception as e:
            print(f"❌ Error loading user signals: {str(e)}")
        
        # Create dev admin user
        self.create_dev_admin()
        
        # Fix existing users (only run in production or when explicitly enabled)
        if self.should_run_user_setup():
            self.setup_existing_users()

    def should_run_user_setup(self):
        """
        Determine if we should run the user setup.
        Only run in production or when explicitly enabled via environment variable.
        """
        # Run if we're on Render (production)
        if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
            return True
        
        # Run if explicitly enabled via environment variable
        if os.environ.get('SETUP_EXISTING_USERS', '').lower() == 'true':
            return True
        
        # Run if DEBUG is False (production)
        from django.conf import settings
        if not getattr(settings, 'DEBUG', True):
            return True
            
        return False

    def setup_existing_users(self):
        """
        Set up basic subscription plans and fix existing users.
        Safe to run multiple times.
        """
        try:
            print("🔧 Setting up existing users...")
            
            # Import models here to avoid AppRegistryNotReady errors
            from django.contrib.auth import get_user_model
            from users.models import UserPreferences, PrayerMethod, PrayerOffset
            from subscriptions.models import SubscriptionPlan, UserSubscription
            from datetime import date
            
            User = get_user_model()
            
            with transaction.atomic():
                # 1. Create subscription plans
                plans_created = self.create_subscription_plans(SubscriptionPlan)
                
                # 2. Fix users in batches to avoid memory issues
                users = User.objects.all()
                total_users = users.count()
                
                if total_users == 0:
                    print("ℹ️ No users found to fix")
                    return
                
                print(f"🔧 Checking {total_users} users...")
                
                fixed_count = 0
                basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
                
                # Process users in batches of 50
                batch_size = 50
                for i in range(0, total_users, batch_size):
                    batch_users = users[i:i + batch_size]
                    
                    for user in batch_users:
                        user_fixed = self.fix_user(
                            user, basic_plan, UserPreferences, 
                            PrayerMethod, PrayerOffset, UserSubscription, date
                        )
                        if user_fixed:
                            fixed_count += 1
                
                print(f"✅ User setup completed! Fixed {fixed_count} out of {total_users} users")
                
                # 3. Print summary
                self.print_setup_summary(User, UserPreferences, SubscriptionPlan, UserSubscription)
                
        except Exception as e:
            print(f"❌ Error during user setup: {str(e)}")
            # Don't raise the error - we don't want to break app startup

    def create_subscription_plans(self, SubscriptionPlan):
        """Create subscription plans if they don't exist"""
        plans_created = 0
        
        # Create basic plan
        basic_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='basic',
            defaults={
                'name': 'Basic Plan',
                'price': 0.00,
                'max_notifications_per_day': 10,
                'features': {
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
            }
        )
        if created:
            print(f"✅ Created basic subscription plan")
            plans_created += 1
        
        # Create premium plan
        premium_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='premium',
            defaults={
                'name': 'Premium Plan',
                'price': 9.99,
                'max_notifications_per_day': 100,
                'features': {
                    'daily_prayer_summary_email': True,
                    'daily_prayer_summary_sms': True,
                    'daily_prayer_summary_whatsapp': True,
                    'pre_adhan_email': True,
                    'pre_adhan_sms': True,
                    'pre_adhan_whatsapp': True,
                    'adhan_call_email': True,
                    'adhan_call_audio': True,
                    'adhan_call_text': True,
                }
            }
        )
        if created:
            print(f"✅ Created premium subscription plan")
            plans_created += 1
            
        return plans_created

    def fix_user(self, user, basic_plan, UserPreferences, PrayerMethod, PrayerOffset, UserSubscription, date):
        """Fix a single user's missing data"""
        user_fixed = False
        
        try:
            # Create UserPreferences if missing
            if not UserPreferences.objects.filter(user=user).exists():
                UserPreferences.objects.create(
                    user=user,
                    daily_prayer_summary_enabled=True,
                    daily_prayer_summary_message_method='email',
                    notification_before_prayer_enabled=True,
                    notification_before_prayer='email',
                    notification_time_before_prayer=15,
                    adhan_call_enabled=True,
                    adhan_call_method='email',
                    notification_methods='email',
                )
                user_fixed = True

            # Create PrayerMethod if missing
            if not PrayerMethod.objects.filter(user=user).exists():
                PrayerMethod.objects.create(
                    user=user,
                    sn=1,
                    name='Muslim World League'
                )
                user_fixed = True

            # Create PrayerOffset if missing
            if not PrayerOffset.objects.filter(user=user).exists():
                PrayerOffset.objects.create(
                    user=user,
                    imsak=0, fajr=0, sunrise=0, dhuhr=0, asr=0,
                    maghrib=0, sunset=0, isha=0, midnight=0
                )
                user_fixed = True

            # Create UserSubscription if missing
            if not UserSubscription.objects.filter(user=user).exists():
                UserSubscription.objects.create(
                    user=user,
                    plan=basic_plan,
                    status='active',
                    start_date=date.today(),
                    end_date=None,  # Basic plan never expires
                    is_trial=False,
                    auto_renew=True,
                )
                user_fixed = True

            if user_fixed:
                print(f"   ✅ Fixed user: {user.username}")
                
        except Exception as e:
            print(f"   ❌ Error fixing user {user.username}: {str(e)}")
            
        return user_fixed

    def print_setup_summary(self, User, UserPreferences, SubscriptionPlan, UserSubscription):
        """Print a summary of the current setup"""
        try:
            total_users = User.objects.count()
            users_with_preferences = UserPreferences.objects.count()
            users_with_subscriptions = UserSubscription.objects.count()
            basic_plan_users = UserSubscription.objects.filter(plan__plan_type='basic').count()
            premium_plan_users = UserSubscription.objects.filter(plan__plan_type='premium').count()
            
            print(f"""
📊 SETUP SUMMARY:
• Total users: {total_users}
• Users with preferences: {users_with_preferences}
• Users with subscriptions: {users_with_subscriptions}
• Basic plan users: {basic_plan_users}
• Premium plan users: {premium_plan_users}
• Setup completion: {(users_with_preferences / total_users * 100):.1f}% if total_users > 0 else 0
            """)
            
        except Exception as e:
            print(f"❌ Error printing summary: {str(e)}")

    def create_dev_admin(self):
        """Create development admin user if it doesn't exist"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            with transaction.atomic():
                if not User.objects.filter(username='admin4').exists():
                    User.objects.create_superuser(
                        username='admin4',
                        email='admin4@example1.com',
                        password='admin123456'
                    )
                    print("✅ Created admin4 user")
        except Exception as e:
            print(f"❌ Could not create admin user: {str(e)}")
