from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class ProviderConfiguration(models.Model):
    """Store provider configurations in database (optional - can use settings.py instead)"""
    
    PROVIDER_TYPES = [
        ('sms', 'SMS Provider'),
        ('call', 'Call Provider'),
        ('whatsapp', 'WhatsApp Provider'),
        ('combined', 'Combined Provider'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    provider_class = models.CharField(max_length=200)  # Full Python path to provider class
    configuration = models.JSONField(default=dict)  # API keys, endpoints, etc.
    supported_countries = models.JSONField(default=list)  # List of country codes
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=100)  # Lower = higher priority
    cost_per_message = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.provider_type})"
    
    def get_config_dict(self):
        """Get configuration as dictionary"""
        return self.configuration
    
    def set_config(self, config_dict):
        """Set configuration from dictionary"""
        self.configuration = config_dict
        self.save()


class CommunicationLog(models.Model):
    """Log all communication attempts for analytics and debugging"""
    
    COMMUNICATION_TYPES = [
        ('sms', 'SMS'),
        ('call', 'Voice Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='communication_logs')
    communication_type = models.CharField(max_length=20, choices=COMMUNICATION_TYPES)
    provider_name = models.CharField(max_length=100)
    recipient = models.CharField(max_length=50)  # Phone number or email (hashed for privacy)
    message_id = models.CharField(max_length=200, null=True, blank=True)
    
    success = models.BooleanField()
    error_message = models.TextField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    
    # Prayer-related context
    prayer_name = models.CharField(max_length=50, null=True, blank=True)
    notification_type = models.CharField(max_length=50, null=True, blank=True)  # daily_summary, pre_adhan, adhan_call
    
    # Technical details
    response_time_ms = models.IntegerField(null=True, blank=True)
    country_code = models.CharField(max_length=2, null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['communication_type', 'created_at']),
            models.Index(fields=['provider_name', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]
    
    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.communication_type} via {self.provider_name} to {self.recipient[:8]}***"


class ProviderStatus(models.Model):
    """Track provider health and performance"""
    
    provider_name = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2)
    
    # Success metrics
    total_attempts = models.IntegerField(default=0)
    successful_attempts = models.IntegerField(default=0)
    failed_attempts = models.IntegerField(default=0)
    
    # Performance metrics
    average_response_time_ms = models.IntegerField(default=0)
    average_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    
    # Health status
    is_healthy = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)
    
    # Time windows
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['provider_name', 'country_code']
        ordering = ['-last_updated']
    
    def __str__(self):
        health = "🟢" if self.is_healthy else "🔴"
        success_rate = (self.successful_attempts / max(self.total_attempts, 1)) * 100
        return f"{health} {self.provider_name} ({self.country_code}): {success_rate:.1f}% success"
    
    @property
    def success_rate(self):
        """Calculate success rate as percentage"""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_attempts) * 100
    
    def update_metrics(self, success: bool, response_time_ms: int = None, cost: float = None):
        """Update metrics with new attempt"""
        self.total_attempts += 1
        
        if success:
            self.successful_attempts += 1
            self.last_success_at = timezone.now()
            self.consecutive_failures = 0
        else:
            self.failed_attempts += 1
            self.last_failure_at = timezone.now()
            self.consecutive_failures += 1
        
        # Update averages
        if response_time_ms:
            if self.average_response_time_ms == 0:
                self.average_response_time_ms = response_time_ms
            else:
                self.average_response_time_ms = int(
                    (self.average_response_time_ms + response_time_ms) / 2
                )
        
        if cost:
            if self.average_cost == 0:
                self.average_cost = cost
            else:
                self.average_cost = (self.average_cost + cost) / 2
        
        # Update health status
        self.is_healthy = (
            self.consecutive_failures < 5 and  # Less than 5 consecutive failures
            self.success_rate >= 80.0  # At least 80% success rate
        )

        self.save()


class VoiceCallSession(models.Model):
    """Store voice call session data for callback retrieval"""

    phone_number = models.CharField(max_length=20, db_index=True)
    session_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    # Call data
    call_type = models.CharField(max_length=20)  # 'adhan_audio', 'tts', etc.
    audio_url = models.URLField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        return f"{self.phone_number} - {self.call_type}"

    @classmethod
    def cleanup_old_sessions(cls):
        """Delete sessions older than 1 hour"""
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=1)
        cls.objects.filter(created_at__lt=cutoff).delete()
