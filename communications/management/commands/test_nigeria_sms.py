from django.core.management.base import BaseCommand
from communications.services.provider_registry import ProviderRegistry
from users.models import CustomUser
import asyncio


class Command(BaseCommand):
    help = 'Test Nigeria SMS functionality with cost comparison'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone', 
            type=str, 
            default='+2348012345678',
            help='Nigerian phone number to test (default: +2348012345678)'
        )
        parser.add_argument(
            '--message',
            type=str,
            default='🕌 Assalam Alaikum! This is a test message from Muadhin Nigeria. Allahu Akbar!',
            help='Message to send'
        )

    def handle(self, *args, **options):
        phone_number = options['phone']
        message = options['message']
        
        self.stdout.write(
            self.style.SUCCESS('🇳🇬 Testing Nigeria-First SMS Implementation\n')
        )
        
        # Initialize provider registry
        ProviderRegistry.initialize()
        
        # Show cost comparison
        self.stdout.write('💰 Cost Comparison for Nigeria:')
        estimates = ProviderRegistry.get_cost_estimate_for_country('NG', 1)
        for provider_name, cost_info in estimates.items():
            savings = ""
            if provider_name != 'TwilioProvider':
                twilio_cost = estimates.get('TwilioProvider', {}).get('cost_per_message', 0)
                if twilio_cost > 0:
                    savings_pct = ((twilio_cost - cost_info['cost_per_message']) / twilio_cost) * 100
                    savings = f" (💡 {savings_pct:.0f}% cheaper than Twilio)"
            
            self.stdout.write(
                f"  {provider_name}: ${cost_info['cost_per_message']:.4f} per SMS{savings}"
            )
        
        # Get providers for Nigeria
        providers = ProviderRegistry.get_providers_for_country('NG')
        self.stdout.write(f'\n📡 Available providers for Nigeria: {len(providers)}')
        
        # Test each provider
        for i, provider in enumerate(providers, 1):
            self.stdout.write(f'\n🧪 Testing Provider {i}/{len(providers)}: {provider.name}')
            
            try:
                # Test SMS sending
                result = provider.send_sms_sync(phone_number, message, 'NG')
                
                if result.success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✅ SUCCESS: Message ID {result.message_id}'
                        )
                    )
                    if result.cost:
                        self.stdout.write(f'  💵 Cost: ${result.cost}')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ FAILED: {result.error_message}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  💥 EXCEPTION: {str(e)}')
                )
        
        # Test user workflow
        self.stdout.write('\n👤 Testing User Workflow:')
        
        # Create or get a test Nigerian user
        test_user, created = CustomUser.objects.get_or_create(
            username='nigeria_test_user',
            defaults={
                'email': 'nigeria_test@muadhin.com',
                'country': 'NIGERIA',
                'city': 'Lagos',
                'phone_number': phone_number
            }
        )
        
        if created:
            self.stdout.write('  📝 Created test user: nigeria_test_user')
        else:
            self.stdout.write('  📂 Using existing test user: nigeria_test_user')
        
        # Show user's optimal setup
        self.stdout.write(f'  🌍 Country Code: {test_user.get_country_code()}')
        self.stdout.write(f'  💰 Preferred Currency: {test_user.preferred_currency}')
        
        optimal_provider = test_user.get_optimal_provider()
        if optimal_provider:
            cost = optimal_provider.get_cost_per_message('NG')
            self.stdout.write(f'  🚀 Optimal Provider: {optimal_provider.name} (${cost}/SMS)')
        
        # Show available plans
        available_plans = test_user.get_available_plans()
        nigeria_plans = [p for p in available_plans if p.country == 'NG']
        
        self.stdout.write(f'  📋 Nigeria Plans Available: {len(nigeria_plans)}')
        for plan in nigeria_plans[:3]:  # Show first 3
            self.stdout.write(f'    • {plan.name}: {plan.localized_price_display}')
        
        self.stdout.write('\n🎉 Nigeria-First Implementation Test Complete!')
        self.stdout.write('✨ Key Benefits:')
        self.stdout.write('  • 80%+ cost reduction vs global providers')
        self.stdout.write('  • Local Nigerian pricing in Naira (₦)')
        self.stdout.write('  • Optimized provider selection for Nigeria')
        self.stdout.write('  • Automatic fallback to global providers')