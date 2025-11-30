from django.contrib import admin
from .models import ProviderConfiguration, CommunicationLog, ProviderStatus, CountryProviderPreference


@admin.register(ProviderConfiguration)
class ProviderConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'is_active', 'priority', 'cost_per_message', 'supported_countries_display')
    list_filter = ('provider_type', 'is_active')
    search_fields = ('name', 'provider_class')
    ordering = ('priority', 'name')
    
    def supported_countries_display(self, obj):
        countries = obj.supported_countries
        if isinstance(countries, list) and countries:
            return ', '.join(countries[:5]) + ('...' if len(countries) > 5 else '')
        return 'None'
    supported_countries_display.short_description = 'Supported Countries'


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'communication_type', 'provider_name', 'success', 'delivery_status', 'prayer_name', 'cost')
    list_filter = ('communication_type', 'provider_name', 'success', 'delivery_status', 'prayer_name', 'created_at')
    search_fields = ('user__username', 'user__email', 'provider_name', 'message_id')
    readonly_fields = ('created_at', 'delivered_at', 'raw_response')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        return False  # Logs are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be modified


@admin.register(ProviderStatus)
class ProviderStatusAdmin(admin.ModelAdmin):
    list_display = ('provider_name', 'country_code', 'is_healthy', 'success_rate_display', 'total_attempts', 'last_updated')
    list_filter = ('is_healthy', 'provider_name', 'country_code')
    search_fields = ('provider_name', 'country_code')
    readonly_fields = ('total_attempts', 'successful_attempts', 'failed_attempts', 'last_success_at', 'last_failure_at', 'created_at', 'last_updated')
    ordering = ('-last_updated',)
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Success Rate'
    
    def has_add_permission(self, request):
        return False  # Status records are created automatically


@admin.register(CountryProviderPreference)
class CountryProviderPreferenceAdmin(admin.ModelAdmin):
    list_display = ('country_code', 'communication_type', 'provider_priority_display', 'is_active', 'updated_at')
    list_filter = ('communication_type', 'is_active', 'country_code')
    search_fields = ('country_code', 'notes')
    ordering = ('country_code', 'communication_type')

    fieldsets = (
        ('Basic Information', {
            'fields': ('country_code', 'communication_type', 'is_active')
        }),
        ('Provider Configuration', {
            'fields': ('provider_priority',),
            'description': 'Enter provider names in priority order as a JSON array. Example: ["nigeria", "africastalking"] means try Nigeria provider first, then Africa\'s Talking.'
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')

    def provider_priority_display(self, obj):
        providers = obj.get_provider_names()
        if providers:
            return ' → '.join(providers)
        return 'No providers configured'
    provider_priority_display.short_description = 'Provider Priority'
