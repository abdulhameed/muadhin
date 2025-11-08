from django.contrib import admin
from django.contrib.admin.helpers import ActionForm
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from .models import CustomUser, UserPreferences, Location, PrayerMethod, PrayerOffset
from subscriptions.models import SubscriptionPlan, UserSubscription
from datetime import date

User = get_user_model()

# Register your models here.


def setup_basic_plan_action(modeladmin, request, queryset):
    """Admin action to set up basic plan and fix users"""
    
    # Check if user is superuser
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can run this action.")
        return
    
    try:
        # 1. Create or get basic subscription plan
        basic_plan, created = SubscriptionPlan.objects.get_or_create(
            plan_type='basic',
            defaults={
                'name': 'Basic Plan',
                'price': 0.00,
                'max_notifications_per_day': 15,
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
            messages.success(request, f'✅ Created basic subscription plan: {basic_plan.name}')
        else:
            messages.info(request, f'ℹ️ Basic subscription plan already exists: {basic_plan.name}')

        # 2. Create premium plan as well
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
            messages.success(request, f'✅ Created premium subscription plan: {premium_plan.name}')

        # Fix users in chunks to avoid memory issues
        chunk_size = 5
        total_users = User.objects.count()
        fixed_count = 0
        
        for offset in range(0, total_users, chunk_size):
            users_chunk = User.objects.select_related(
                'preferences', 'prayer_method', 'prayer_offset', 'subscription'
            )[offset:offset + chunk_size]
            
            for user in users_chunk:
                user_fixed = False
                
                # Create missing related objects
                if not hasattr(user, 'preferences'):
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
            if not hasattr(user, 'prayer_method'):
                PrayerMethod.objects.create(
                    user=user,
                    sn=1,
                    name='Muslim World League'
                )
                user_fixed = True

            # Create PrayerOffset if missing
            if not hasattr(user, 'prayer_offset'):
                PrayerOffset.objects.create(
                    user=user,
                    imsak=0, fajr=0, sunrise=0, dhuhr=0, asr=0,
                    maghrib=0, sunset=0, isha=0, midnight=0
                )
                user_fixed = True

            # Create UserSubscription if missing
            if not hasattr(user, 'subscription'):
                UserSubscription.objects.create(
                    user=user,
                    plan=basic_plan,
                    status='active',
                    start_date=date.today(),
                    end_date=None,
                    is_trial=False,
                    auto_renew=True,
                )
                user_fixed = True

            if user_fixed:
                fixed_count += 1

        # Clear Django query cache after each chunk
        from django.db import connection
        connection.queries_log.clear()

        messages.success(request, f'🎉 Setup completed! Fixed {fixed_count} users with basic plan.')
        
    except Exception as e:
        messages.error(request, f'❌ Error during setup: {str(e)}')

setup_basic_plan_action.short_description = "🔧 Setup Basic Plan & Fix All Users"


def diagnose_users_action(modeladmin, request, queryset):
    """Admin action to diagnose user setup issues"""
    
    # Check if user is superuser
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can run this action.")
        return
    
    try:
        # Check subscription plans
        basic_exists = SubscriptionPlan.objects.filter(plan_type='basic').exists()
        premium_exists = SubscriptionPlan.objects.filter(plan_type='premium').exists()
        
        # Check users
        total_users = User.objects.count()
        missing_preferences = User.objects.filter(preferences__isnull=True).count()
        missing_prayer_method = User.objects.filter(prayer_method__isnull=True).count()
        missing_subscription = User.objects.filter(subscription__isnull=True).count()
        
        # Email-only users (basic plan users)
        email_only_users = 0
        try:
            email_only_users = UserPreferences.objects.filter(
                daily_prayer_summary_message_method='email',
                notification_before_prayer='email',
                adhan_call_method='email'
            ).count()
        except:
            pass

        # Create diagnostic message
        diagnostic_msg = f"""
📊 DIAGNOSTIC REPORT:
• Basic plan exists: {'✅' if basic_exists else '❌'}
• Premium plan exists: {'✅' if premium_exists else '⚠️'}
• Total users: {total_users}
• Missing preferences: {missing_preferences}
• Missing prayer method: {missing_prayer_method}
• Missing subscription: {missing_subscription}
• Email-only users (basic): {email_only_users}
        """

        if any([missing_preferences, missing_prayer_method, missing_subscription]):
            messages.warning(request, diagnostic_msg + "\n💡 Run 'Setup Basic Plan & Fix All Users' action to fix issues.")
        else:
            messages.success(request, diagnostic_msg + "\n🎉 All users are properly configured!")
            
    except Exception as e:
        messages.error(request, f'❌ Error during diagnosis: {str(e)}')

diagnose_users_action.short_description = "🔍 Diagnose User Setup"


class UserSubscriptionInline(admin.StackedInline):
    model = UserSubscription
    extra = 0
    max_num = 1
    can_delete = False
    fields = ('plan', 'status', 'start_date', 'end_date', 'trial_end_date')
    readonly_fields = ('created_at', 'updated_at')
    verbose_name = 'Subscription'
    verbose_name_plural = 'Subscription'


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'sex', 'city', 'country', 'timezone', 'phone_number', 'subscription_plan', 'subscription_status', 'last_scheduled_time', 'midnight_utc')
    list_filter = ('sex', 'country', 'timezone', 'subscription__status', 'subscription__plan__plan_type')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    actions = [setup_basic_plan_action, diagnose_users_action]
    inlines = [UserSubscriptionInline]
    list_select_related = ('subscription', 'subscription__plan')

    def subscription_plan(self, obj):
        if hasattr(obj, 'subscription') and obj.subscription:
            return obj.subscription.plan.name
        return '❌ No plan'
    subscription_plan.short_description = 'Subscription Plan'
    subscription_plan.admin_order_field = 'subscription__plan__name'

    def subscription_status(self, obj):
        if hasattr(obj, 'subscription') and obj.subscription:
            if obj.subscription.is_active:
                return '✅ Active'
            else:
                return f'❌ {obj.subscription.status}'
        return '❌ None'
    subscription_status.short_description = 'Status'
    subscription_status.admin_order_field = 'subscription__status'

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Only show setup actions to superusers
        if not request.user.is_superuser:
            if 'setup_basic_plan_action' in actions:
                del actions['setup_basic_plan_action']
            if 'diagnose_users_action' in actions:
                del actions['diagnose_users_action']
        return actions


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_methods', 'utc_time_for_1159')
    actions = [setup_basic_plan_action, diagnose_users_action]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            if 'setup_basic_plan_action' in actions:
                del actions['setup_basic_plan_action']
            if 'diagnose_users_action' in actions:
                del actions['diagnose_users_action']
        return actions

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('user', 'latitude', 'longitude', 'timezone')

@admin.register(PrayerMethod)
class PrayerMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_name')

@admin.register(PrayerOffset)
class PrayerOffsetAdmin(admin.ModelAdmin):
    list_display = ('user', 'imsak', 'fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'sunset', 'isha', 'midnight', 'created_at', 'updated_at')
