from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from django.utils import timezone

# User = get_user_model()

class SubscriptionPlan(models.Model):
    PLAN_TYPES = [
        ('basic', 'Basic - Salah Reminder'),
        ('plus', 'Plus - Muaddhin'),
        ('premium', 'Premium - Qiyam'),
    ]
    
    BILLING_CYCLES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('lifetime', 'Lifetime'),
    ]
    
    COUNTRIES = [
        ('GLOBAL', 'Global'),
        ('NG', 'Nigeria'),
        ('UK', 'United Kingdom'),
        ('CA', 'Canada'),
        ('AU', 'Australia'),
        ('AE', 'United Arab Emirates'),
        ('SA', 'Saudi Arabia'),
        ('QA', 'Qatar'),
    ]
    
    CURRENCIES = [
        ('USD', 'US Dollar'),
        ('NGN', 'Nigerian Naira'),
        ('GBP', 'British Pound'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
        ('AED', 'UAE Dirham'),
        ('SAR', 'Saudi Riyal'),
        ('QAR', 'Qatari Riyal'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    country = models.CharField(max_length=10, choices=COUNTRIES, default='GLOBAL')
    currency = models.CharField(max_length=3, choices=CURRENCIES, default='USD')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, default='monthly')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Feature flags for notifications
    daily_prayer_summary_email = models.BooleanField(default=True)
    daily_prayer_summary_sms = models.BooleanField(default=False)
    daily_prayer_summary_whatsapp = models.BooleanField(default=False)
    
    pre_adhan_email = models.BooleanField(default=True)
    pre_adhan_sms = models.BooleanField(default=False)
    pre_adhan_whatsapp = models.BooleanField(default=False)
    
    adhan_call_text = models.BooleanField(default=False)
    adhan_call_audio = models.BooleanField(default=False)
    
    # Additional features
    max_notifications_per_day = models.IntegerField(default=10)
    priority_support = models.BooleanField(default=False)
    custom_adhan_sounds = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['country', 'sort_order', 'price']
        unique_together = ['plan_type', 'country', 'billing_cycle']
    
    def __str__(self):
        if self.country == 'GLOBAL':
            return f"{self.name} - {self.currency} {self.price}"
        else:
            country_name = dict(self.COUNTRIES)[self.country]
            return f"{self.name} ({country_name}) - {self.currency} {self.price}"
    
    @property
    def features_list(self):
        """Return a list of enabled features for this plan"""
        features = []
        if self.daily_prayer_summary_email:
            features.append("Daily Prayer Summary (Email)")
        if self.daily_prayer_summary_sms:
            features.append("Daily Prayer Summary (SMS)")
        if self.daily_prayer_summary_whatsapp:
            features.append("Daily Prayer Summary (WhatsApp)")
        if self.pre_adhan_email:
            features.append("Pre-Adhan Notifications (Email)")
        if self.pre_adhan_sms:
            features.append("Pre-Adhan Notifications (SMS)")
        if self.pre_adhan_whatsapp:
            features.append("Pre-Adhan Notifications (WhatsApp)")
        if self.adhan_call_text:
            features.append("Adhan Call (Text)")
        if self.adhan_call_audio:
            features.append("Adhan Call (Audio)")
        if self.priority_support:
            features.append("Priority Support")
        if self.custom_adhan_sounds:
            features.append("Custom Adhan Sounds")
        return features
    
    @classmethod
    def get_plans_for_country(cls, country_code):
        """Get active subscription plans for a specific country"""
        return cls.objects.filter(
            country__in=[country_code.upper(), 'GLOBAL'],
            is_active=True
        ).order_by('country', 'sort_order')
    
    @classmethod
    def get_best_plan_for_country(cls, plan_type, country_code):
        """Get the best plan for a country (country-specific first, then global)"""
        # Try country-specific first
        country_plan = cls.objects.filter(
            plan_type=plan_type,
            country=country_code.upper(),
            is_active=True
        ).first()
        
        if country_plan:
            return country_plan
        
        # Fallback to global plan
        return cls.objects.filter(
            plan_type=plan_type,
            country='GLOBAL',
            is_active=True
        ).first()
    
    @property
    def localized_price_display(self):
        """Display price in local format"""
        if self.currency == 'NGN':
            return f"₦{self.price:,.0f}"
        elif self.currency == 'USD':
            return f"${self.price}"
        elif self.currency == 'GBP':
            return f"£{self.price}"
        elif self.currency == 'EUR':
            return f"€{self.price}"
        else:
            return f"{self.currency} {self.price}"


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('trial', 'Trial'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    trial_end_date = models.DateTimeField(null=True, blank=True)
    
    # Payment integration fields
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    notifications_sent_today = models.IntegerField(default=0)
    last_usage_reset = models.DateField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is currently active"""
        now = timezone.now()
        
        if self.status == 'trial':
            return self.trial_end_date and now <= self.trial_end_date
        
        if self.status == 'active':
            if self.end_date:
                return now <= self.end_date
            return True
        
        return False
    
    @property
    def is_trial(self):
        """Check if user is on trial"""
        return (self.status == 'trial' and 
                self.trial_end_date and 
                timezone.now() <= self.trial_end_date)
    
    @property
    def days_remaining(self):
        """Get days remaining in subscription"""
        if not self.is_active:
            return 0
        
        end_date = self.trial_end_date if self.is_trial else self.end_date
        if end_date:
            remaining = end_date - timezone.now()
            return max(0, remaining.days)
        return None  # Lifetime/no expiry
    
    def can_use_feature(self, feature_name):
        """Check if user can use a specific feature"""
        if not self.is_active:
            return False
        
        # Check daily limits
        if feature_name in ['sms', 'whatsapp', 'email']:
            self._reset_daily_usage_if_needed()
            if self.notifications_sent_today >= self.plan.max_notifications_per_day:
                return False
        
        return getattr(self.plan, feature_name, False)
    
    def increment_usage(self):
        """Increment daily usage counter"""
        self._reset_daily_usage_if_needed()
        self.notifications_sent_today += 1
        self.save(update_fields=['notifications_sent_today'])
    
    def _reset_daily_usage_if_needed(self):
        """Reset usage counter if it's a new day"""
        today = timezone.now().date()
        if self.last_usage_reset < today:
            self.notifications_sent_today = 0
            self.last_usage_reset = today
            self.save(update_fields=['notifications_sent_today', 'last_usage_reset'])
    
    def start_trial(self, trial_days=7):
        """Start a trial period"""
        self.status = 'trial'
        self.trial_end_date = timezone.now() + timedelta(days=trial_days)
        self.save()
    
    def activate_subscription(self, end_date=None):
        """Activate the subscription"""
        self.status = 'active'
        self.start_date = timezone.now()
        if end_date:
            self.end_date = end_date
        self.save()
    
    def cancel_subscription(self):
        """Cancel the subscription"""
        self.status = 'cancelled'
        self.save()


class SubscriptionHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription_history')
    from_plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.CASCADE, 
        related_name='upgrades_from',
        null=True, blank=True
    )
    to_plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.CASCADE, 
        related_name='upgrades_to'
    )
    change_date = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=100, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['-change_date']
        verbose_name_plural = "Subscription histories"
    
    def __str__(self):
        from_plan_name = self.from_plan.name if self.from_plan else "No Plan"
        return f"{self.user.username}: {from_plan_name} → {self.to_plan.name}"


class NotificationUsage(models.Model):
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('call', 'Phone Call'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_usage')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    date_sent = models.DateTimeField(auto_now_add=True)
    prayer_name = models.CharField(max_length=50, null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_sent']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification_type} ({self.date_sent.date()})"
