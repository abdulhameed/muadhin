from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory, NotificationUsage


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'price', 'billing_cycle', 'is_active', 'sort_order')
    list_filter = ('plan_type', 'billing_cycle', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('sort_order', 'price')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_type', 'price', 'billing_cycle', 'description', 'is_active', 'sort_order')
        }),
        ('Daily Prayer Summary Features', {
            'fields': ('daily_prayer_summary_email', 'daily_prayer_summary_whatsapp')
        }),
        ('Pre-Adhan Notification Features', {
            'fields': ('pre_adhan_email', 'pre_adhan_sms', 'pre_adhan_whatsapp')
        }),
        ('Adhan Call Features', {
            'fields': ('adhan_call_text', 'adhan_call_audio')
        }),
        ('Additional Features', {
            'fields': ('max_notifications_per_day', 'priority_support', 'custom_adhan_sounds')
        }),
    )


@admin.register(UserSubscription) 
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'is_active')
    list_filter = ('status', 'plan', 'start_date')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    
    readonly_fields = ('created_at', 'updated_at', 'is_active', 'is_trial', 'days_remaining')
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'trial_end_date')
        }),
        ('Payment Information', {
            'fields': ('stripe_subscription_id', 'stripe_customer_id', 'last_payment_date', 'next_billing_date')
        }),
        ('Usage Tracking', {
            'fields': ('notifications_sent_today', 'last_usage_reset')
        }),
        ('Computed Fields', {
            'fields': ('is_active', 'is_trial', 'days_remaining'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_plan', 'to_plan', 'change_date', 'reason')
    list_filter = ('change_date', 'reason', 'to_plan')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    readonly_fields = ('change_date',)


@admin.register(NotificationUsage)
class NotificationUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'prayer_name', 'date_sent', 'success')
    list_filter = ('notification_type', 'success', 'date_sent', 'prayer_name')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    readonly_fields = ('date_sent',)
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation
