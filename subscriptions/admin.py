from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory, NotificationUsage


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'country', 'currency', 'price', 'billing_cycle', 'is_active', 'sort_order')
    list_filter = ('plan_type', 'billing_cycle', 'country', 'currency', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('country', 'sort_order', 'price')
    list_editable = ('is_active', 'sort_order')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'plan_type', 'country', 'currency', 'price', 'billing_cycle', 'description', 'is_active', 'sort_order')
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

    def get_readonly_fields(self, request, obj=None):
        # Make country and currency readonly after creation to prevent breaking unique constraints
        if obj:  # Editing an existing object
            return ('country', 'currency', 'plan_type', 'billing_cycle')
        return ()


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'is_active_display', 'days_remaining_display')
    list_filter = ('status', 'plan__plan_type', 'plan__country', 'start_date')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)
    list_select_related = ('user', 'plan')
    date_hierarchy = 'start_date'

    readonly_fields = ('created_at', 'updated_at', 'is_active', 'is_trial', 'days_remaining')

    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'plan', 'status'),
            'description': 'Assign a subscription plan to the user. The plan will determine available features.'
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'trial_end_date'),
            'description': 'Set start and end dates. Leave end_date blank for lifetime subscriptions.'
        }),
        ('Payment Information', {
            'fields': ('stripe_subscription_id', 'stripe_customer_id', 'last_payment_date', 'next_billing_date'),
            'classes': ('collapse',)
        }),
        ('Usage Tracking', {
            'fields': ('notifications_sent_today', 'last_usage_reset'),
            'classes': ('collapse',)
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

    def is_active_display(self, obj):
        return '✅' if obj.is_active else '❌'
    is_active_display.short_description = 'Active'
    is_active_display.admin_order_field = 'status'

    def days_remaining_display(self, obj):
        days = obj.days_remaining
        if days is None:
            return '∞ Lifetime'
        elif days == 0:
            return '⚠️ Expired'
        elif days <= 7:
            return f'⚠️ {days} days'
        else:
            return f'{days} days'
    days_remaining_display.short_description = 'Remaining'

    actions = ['activate_subscriptions', 'cancel_subscriptions', 'start_trial']

    def activate_subscriptions(self, request, queryset):
        count = 0
        for subscription in queryset:
            subscription.activate_subscription()
            count += 1
        self.message_user(request, f'Successfully activated {count} subscription(s).')
    activate_subscriptions.short_description = 'Activate selected subscriptions'

    def cancel_subscriptions(self, request, queryset):
        count = queryset.update(status='cancelled')
        self.message_user(request, f'Successfully cancelled {count} subscription(s).')
    cancel_subscriptions.short_description = 'Cancel selected subscriptions'

    def start_trial(self, request, queryset):
        count = 0
        for subscription in queryset:
            subscription.start_trial(trial_days=7)
            count += 1
        self.message_user(request, f'Successfully started 7-day trial for {count} subscription(s).')
    start_trial.short_description = 'Start 7-day trial for selected subscriptions'


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
