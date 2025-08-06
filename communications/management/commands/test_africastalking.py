from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from communications.services.notification_service import NotificationService
from communications.services.provider_registry import ProviderRegistry
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()


class Command(BaseCommand):
    help = 'Test AfricasTalking SMS and Voice services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Phone number to test with (include country code, e.g., +234XXXXXXXXX)'
        )
        parser.add_argument(
            '--test-sms',
            action='store_true',
            help='Test SMS sending'
        )
        parser.add_argument(
            '--test-voice',
            action='store_true',
            help='Test voice call'
        )
        parser.add_argument(
            '--provider',
            type=str,
            default='africastalking',
            help='Provider to test (default: africastalking)'
        )

    def handle(self, *args, **options):
        phone_number = options['phone']
        test_sms = options['test_sms']
        test_voice = options['test_voice']
        provider_name = options['provider']

        self.stdout.write(
            self.style.SUCCESS(f'🧪 Testing {provider_name} with phone: {phone_number}')
        )

        try:
            # Initialize the registry properly
            if not ProviderRegistry._initialized():
                ProviderRegistry.initialize_registry()
                self.stdout.write('✅ Provider registry initialized')
            
            # Get the provider
            provider = ProviderRegistry.get_provider(provider_name)
            if not provider:
                self.stdout.write(
                    self.style.ERROR(f'❌ Provider "{provider_name}" not found or not configured')
                )
                return

            self.stdout.write(f'✅ Provider "{provider_name}" loaded successfully')

            # Create a mock user for testing
            mock_user = self._create_mock_user(phone_number)

            # Test SMS if requested
            if test_sms:
                self._test_sms(mock_user, provider_name)

            # Test Voice if requested  
            if test_voice:
                self._test_voice(mock_user, provider_name)

            # If no specific test requested, test SMS by default
            if not test_sms and not test_voice:
                self._test_sms(mock_user, provider_name)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during testing: {str(e)}')
            )
            logger.exception("Error in test_africastalking command")

    def _create_mock_user(self, phone_number):
        """Create a mock user object for testing"""
        class MockUser:
            def __init__(self, phone):
                self.phone_number = phone
                self.whatsapp_number = phone
                self.country = 'NG' if phone.startswith('+234') else 'US'
                self.username = 'test_user'
                self.email = 'test@example.com'
                self.id = 999999  # Fake ID for testing

        return MockUser(phone_number)

    def _test_sms(self, user, provider_name):
        """Test SMS sending"""
        self.stdout.write('📱 Testing SMS...')
        
        test_message = f"🧪 Test SMS from Muadhin via {provider_name}. This is a test message. Time: {self._get_current_time()}"
        
        try:
            result = NotificationService.send_sms(
                user=user,
                message=test_message,
                preferred_provider=provider_name,
                log_usage=False  # Don't log test messages
            )
            
            if result.success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ SMS sent successfully!')
                )
                self.stdout.write(f'   Provider: {result.provider_name}')
                self.stdout.write(f'   Message ID: {result.message_id}')
                if result.cost:
                    self.stdout.write(f'   Cost: {result.cost}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ SMS failed: {result.error_message}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ SMS test exception: {str(e)}')
            )

    def _test_voice(self, user, provider_name):
        """Test voice call"""
        self.stdout.write('📞 Testing Voice Call...')
        
        # Use a test audio URL or TTS message
        test_audio_url = "https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3"
        
        try:
            result = NotificationService.make_call(
                user=user,
                audio_url=test_audio_url,
                preferred_provider=provider_name,
                log_usage=False  # Don't log test calls
            )
            
            if result.success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Voice call initiated successfully!')
                )
                self.stdout.write(f'   Provider: {result.provider_name}')
                self.stdout.write(f'   Call ID: {result.message_id}')
                if result.cost:
                    self.stdout.write(f'   Cost: {result.cost}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Voice call failed: {result.error_message}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Voice call test exception: {str(e)}')
            )

    def _get_current_time(self):
        """Get current time for test message"""
        from django.utils import timezone
        return timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    def _show_provider_config(self, provider_name):
        """Show provider configuration (without sensitive data)"""
        config = settings.COMMUNICATION_PROVIDERS.get(provider_name, {})
        
        self.stdout.write(f'\n📋 {provider_name} Configuration:')
        for key, value in config.items():
            if 'key' in key.lower() or 'token' in key.lower() or 'password' in key.lower():
                # Hide sensitive data
                display_value = f"{'*' * (len(str(value)) - 4)}{str(value)[-4:]}" if value else "Not set"
            else:
                display_value = value if value else "Not set"
            
            self.stdout.write(f'   {key}: {display_value}')


# Quick setup verification script
def verify_africastalking_setup():
    """
    Quick verification that Africa's Talking is properly set up
    Run this in Django shell: exec(open('verify_at_setup.py').read())
    """
    
    print("🔍 Verifying Africa's Talking Setup...")
    print("=" * 40)
    
    # Check environment variables
    import os
    required_vars = ['AFRICASTALKING_USERNAME', 'AFRICASTALKING_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
    else:
        print("✅ Environment variables configured")
    
    # Check provider registry
    try:
        from communications.services.provider_registry import ProviderRegistry
        ProviderRegistry.initialize()
        
        at_provider = ProviderRegistry.get_provider('africastalking')
        if at_provider:
            print(f"✅ Africa's Talking provider loaded: {at_provider.name}")
            print(f"   Configured: {at_provider.is_configured}")
            print(f"   Supported countries: {len(at_provider.get_supported_countries())}")
        else:
            print("❌ Africa's Talking provider not found")
    except Exception as e:
        print(f"❌ Provider registry error: {e}")
    
    # Check country preferences
    try:
        ng_providers = ProviderRegistry.get_providers_for_country('NG')
        provider_names = [p.name for p in ng_providers]
        
        if 'AfricasTalkingProvider' in provider_names[0]:
            print("✅ Africa's Talking is prioritized for Nigeria")
        else:
            print(f"⚠️ Provider priority for NG: {provider_names}")
    except Exception as e:
        print(f"❌ Country preference error: {e}")
    
    # Check migrations
    try:
        from django.core.management import execute_from_command_line
        import sys
        
        print("\n📋 Migration Status:")
        print("Run: python manage.py showmigrations communications")
    except Exception as e:
        print(f"❌ Migration check error: {e}")
    
    print("\n🎯 Next Steps:")
    print("1. Set your Africa's Talking credentials in .env")
    print("2. Run: python manage.py migrate")
    print("3. Test: python manage.py test_africastalking --phone=+2348123456789 --test-sms")


if __name__ == "__main__":
    verify_africastalking_setup()
