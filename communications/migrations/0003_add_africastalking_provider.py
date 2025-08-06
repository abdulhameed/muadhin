from django.db import migrations


def create_africastalking_provider(apps, schema_editor):
    """Add Africa's Talking provider configuration"""
    ProviderConfiguration = apps.get_model('communications', 'ProviderConfiguration')
    
    # Add Africa's Talking provider
    ProviderConfiguration.objects.get_or_create(
        name='africastalking',
        defaults={
            'provider_type': 'combined',
            'provider_class': 'communications.providers.africas_talking_provider.AfricasTalkingProvider',
            'supported_countries': [
                'NG', 'KE', 'UG', 'TZ', 'RW', 'MW', 'ZM', 'GH', 
                'CM', 'CI', 'SN', 'BF', 'ML', 'NE', 'TD'
            ],
            'priority': 5,  # Higher priority than others for African countries
            'cost_per_message': 0.012,  # Average cost
            'is_active': True,
        }
    )
    
    # Update Nigeria provider to lower priority (since AT covers Nigeria better)
    try:
        nigeria_provider = ProviderConfiguration.objects.get(name='nigeria')
        nigeria_provider.priority = 15  # Lower priority than Africa's Talking
        nigeria_provider.save()
    except ProviderConfiguration.DoesNotExist:
        pass


def reverse_africastalking_provider(apps, schema_editor):
    """Remove Africa's Talking provider configuration"""
    ProviderConfiguration = apps.get_model('communications', 'ProviderConfiguration')
    ProviderConfiguration.objects.filter(name='africastalking').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('communications', '0002_seed_providers'),
    ]

    operations = [
        migrations.RunPython(
            create_africastalking_provider,
            reverse_africastalking_provider
        ),
    ]
