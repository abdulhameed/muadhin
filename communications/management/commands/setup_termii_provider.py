from django.core.management.base import BaseCommand
from communications.models import CountryProviderPreference


class Command(BaseCommand):
    help = 'Set up Termii provider configuration for Nigerian users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing configuration'
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)

        self.stdout.write(
            self.style.SUCCESS('🇳🇬 Setting up Termii provider for Nigeria\n')
        )

        # Configure SMS for Nigeria
        self.stdout.write('📱 Configuring SMS provider preferences...')

        sms_preference, created = CountryProviderPreference.objects.get_or_create(
            country_code='NG',
            communication_type='sms',
            defaults={
                'provider_priority': ['nigeria', 'africastalking'],
                'is_active': True,
                'notes': 'Termii first for cost savings, Africa\'s Talking as fallback'
            }
        )

        if not created and reset:
            sms_preference.provider_priority = ['nigeria', 'africastalking']
            sms_preference.is_active = True
            sms_preference.notes = 'Termii first for cost savings, Africa\'s Talking as fallback'
            sms_preference.save()
            self.stdout.write(
                self.style.SUCCESS('  ✅ Updated SMS preference: Termii → Africa\'s Talking')
            )
        elif created:
            self.stdout.write(
                self.style.SUCCESS('  ✅ Created SMS preference: Termii → Africa\'s Talking')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️ SMS preference already exists: {" → ".join(sms_preference.provider_priority)}')
            )

        # Configure Voice Calls for Nigeria
        self.stdout.write('\n📞 Configuring Voice Call provider preferences...')

        call_preference, created = CountryProviderPreference.objects.get_or_create(
            country_code='NG',
            communication_type='call',
            defaults={
                'provider_priority': ['africastalking'],
                'is_active': True,
                'notes': 'Africa\'s Talking for voice calls (Termii doesn\'t support calls yet)'
            }
        )

        if not created and reset:
            call_preference.provider_priority = ['africastalking']
            call_preference.is_active = True
            call_preference.notes = 'Africa\'s Talking for voice calls (Termii doesn\'t support calls yet)'
            call_preference.save()
            self.stdout.write(
                self.style.SUCCESS('  ✅ Updated Call preference: Africa\'s Talking')
            )
        elif created:
            self.stdout.write(
                self.style.SUCCESS('  ✅ Created Call preference: Africa\'s Talking')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️ Call preference already exists: {" → ".join(call_preference.provider_priority)}')
            )

        # Configure WhatsApp for Nigeria
        self.stdout.write('\n💬 Configuring WhatsApp provider preferences...')

        whatsapp_preference, created = CountryProviderPreference.objects.get_or_create(
            country_code='NG',
            communication_type='whatsapp',
            defaults={
                'provider_priority': ['africastalking'],
                'is_active': True,
                'notes': 'Africa\'s Talking for WhatsApp (fallback to SMS if WhatsApp unavailable)'
            }
        )

        if not created and reset:
            whatsapp_preference.provider_priority = ['africastalking']
            whatsapp_preference.is_active = True
            whatsapp_preference.notes = 'Africa\'s Talking for WhatsApp (fallback to SMS if WhatsApp unavailable)'
            whatsapp_preference.save()
            self.stdout.write(
                self.style.SUCCESS('  ✅ Updated WhatsApp preference: Africa\'s Talking')
            )
        elif created:
            self.stdout.write(
                self.style.SUCCESS('  ✅ Created WhatsApp preference: Africa\'s Talking')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️ WhatsApp preference already exists: {" → ".join(whatsapp_preference.provider_priority)}')
            )

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\n✨ Termii Provider Setup Complete!\n'))
        self.stdout.write('Configuration Summary:')
        self.stdout.write(f'  SMS:      {" → ".join(sms_preference.provider_priority)}')
        self.stdout.write(f'  Calls:    {" → ".join(call_preference.provider_priority)}')
        self.stdout.write(f'  WhatsApp: {" → ".join(whatsapp_preference.provider_priority)}')
        self.stdout.write('\n💡 Next Steps:')
        self.stdout.write('  1. Add your Termii credentials to .env:')
        self.stdout.write('     - TERMII_API_KEY=your-api-key')
        self.stdout.write('     - TERMII_SENDER_ID=YourSenderID')
        self.stdout.write('  2. Restart your application')
        self.stdout.write('  3. Test with: python manage.py test_nigeria_sms')
        self.stdout.write('\n📚 You can change these priorities anytime in Django Admin:')
        self.stdout.write('   → Communications → Country Provider Preferences')
        self.stdout.write('=' * 60 + '\n')
