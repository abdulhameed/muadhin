from typing import Dict, List, Optional, Type
from django.conf import settings
import logging

from communications.providers.africas_talking_provider import AfricasTalkingProvider

from ..providers.base import BaseProvider, SMSProvider, CallProvider, WhatsAppProvider
from ..providers.twilio_provider import TwilioProvider
from ..providers.nigeria_provider import NigeriaProvider
from ..providers.india_provider import IndiaProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for all communication providers"""
    
    _providers: Dict[str, BaseProvider] = {}
    _country_preferences: Dict[str, List[str]] = {}
    _initialized = False
    
@classmethod
def initialize(cls):
    """Initialize all providers with their configurations"""
    if cls._initialized:
        return
    
    try:
        # Get provider configurations from settings
        provider_configs = getattr(settings, 'COMMUNICATION_PROVIDERS', {})
        
        # Initialize Twilio (always available as fallback)
        twilio_config = provider_configs.get('twilio', {
            'account_sid': getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
            'auth_token': getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
            'phone_number': getattr(settings, 'TWILIO_PHONE_NUMBER', ''),
            'whatsapp_number': getattr(settings, 'TWILIO_WHATSAPP_NUMBER', ''),
            'debug_mode': getattr(settings, 'DEBUG', True)
        })
        
        if twilio_config.get('account_sid'):
            cls._providers['twilio'] = TwilioProvider(twilio_config)
            logger.info("✅ Twilio provider initialized")
        
        # Initialize Africa's Talking provider (BEST for African countries)
        at_config = provider_configs.get('africastalking', {
            'username': '',
            'api_key': '',
            'sender_id': 'Muadhin',
            'phone_number': '',  # Your AT phone number
            'caller_id': '',     # Caller ID for voice calls
            'debug_mode': getattr(settings, 'DEBUG', True)
        })
        
        if at_config.get('api_key') or at_config.get('debug_mode'):
            cls._providers['africastalking'] = AfricasTalkingProvider(at_config)
            logger.info("✅ Africa's Talking provider initialized")
        
        # Initialize Nigeria provider (SMS only, fallback to AT for calls)
        nigeria_config = provider_configs.get('nigeria', {
            'api_key': '',
            'sender_id': 'Muadhin',
            'api_url': 'https://api.termii.com/api/sms/send',
            'debug_mode': getattr(settings, 'DEBUG', True)
        })
        
        if nigeria_config.get('api_key') or nigeria_config.get('debug_mode'):
            cls._providers['nigeria'] = NigeriaProvider(nigeria_config)
            logger.info("✅ Nigeria provider initialized")
        
        # Initialize India provider
        india_config = provider_configs.get('india', {
            'api_key': '',
            'sender_id': 'MUADHN',
            'api_url': 'https://api.textlocal.in/send/',
            'debug_mode': getattr(settings, 'DEBUG', True)
        })
        
        if india_config.get('api_key') or india_config.get('debug_mode'):
            cls._providers['india'] = IndiaProvider(india_config)
            logger.info("✅ India provider initialized")
        
        # Set up country preferences (UPDATED with Africa's Talking priority)
        cls._country_preferences = {
            # African countries - Africa's Talking first, then local providers, then Twilio
            'NG': ['africastalking', 'nigeria', 'twilio'],  # Nigeria: AT > Local > Twilio
            'KE': ['africastalking', 'twilio'],             # Kenya: AT home country
            'UG': ['africastalking', 'twilio'],             # Uganda: AT strong presence
            'TZ': ['africastalking', 'twilio'],             # Tanzania: AT coverage
            'RW': ['africastalking', 'twilio'],             # Rwanda: AT coverage
            'MW': ['africastalking', 'twilio'],             # Malawi: AT coverage
            'ZM': ['africastalking', 'twilio'],             # Zambia: AT coverage
            'GH': ['africastalking', 'nigeria', 'twilio'],  # Ghana: AT > Nigeria > Twilio
            'CM': ['africastalking', 'twilio'],             # Cameroon: AT coverage
            'CI': ['africastalking', 'twilio'],             # Côte d'Ivoire: AT coverage
            'SN': ['africastalking', 'twilio'],             # Senegal: AT coverage
            'BF': ['africastalking', 'twilio'],             # Burkina Faso: AT coverage
            'ML': ['africastalking', 'twilio'],             # Mali: AT coverage
            'NE': ['africastalking', 'twilio'],             # Niger: AT coverage
            'TD': ['africastalking', 'twilio'],             # Chad: AT coverage
            
            # Asian countries
            'IN': ['india', 'twilio'],      # India: local first
            'BD': ['india', 'twilio'],      # Bangladesh: can use India
            'LK': ['india', 'twilio'],      # Sri Lanka: can use India
            'NP': ['india', 'twilio'],      # Nepal: can use India
            
            # Western countries - Twilio only
            'US': ['twilio'],               # USA: Twilio
            'GB': ['twilio'],               # UK: Twilio
            'CA': ['twilio'],               # Canada: Twilio
            'AU': ['twilio'],               # Australia: Twilio
            'DE': ['twilio'],               # Germany: Twilio
            'FR': ['twilio'],               # France: Twilio
        }
        
        cls._initialized = True
        logger.info(f"✅ Provider registry initialized with {len(cls._providers)} providers")
        
    except Exception as e:
        logger.error(f"❌ Error initializing provider registry: {e}")
        # Ensure at least basic Twilio fallback works
        if 'twilio' not in cls._providers:
            cls._providers['twilio'] = TwilioProvider({'debug_mode': True})

    
    @classmethod
    def get_provider(cls, provider_name: str) -> Optional[BaseProvider]:
        """Get a specific provider by name"""
        if not cls._initialized:
            cls.initialize()
        return cls._providers.get(provider_name)
    
    @classmethod
    def get_providers_for_country(cls, country_code: str) -> List[BaseProvider]:
        """Get ordered list of providers for a country (best first)"""
        if not cls._initialized:
            cls.initialize()
        
        provider_names = cls._country_preferences.get(
            country_code.upper(), 
            ['twilio']  # Default to Twilio
        )
        
        providers = []
        for name in provider_names:
            provider = cls._providers.get(name)
            if provider and provider.is_configured:
                providers.append(provider)
        
        # Always ensure Twilio is available as final fallback
        twilio = cls._providers.get('twilio')
        if twilio and twilio not in providers:
            providers.append(twilio)
        
        return providers
    
    @classmethod
    def get_all_providers(cls) -> Dict[str, BaseProvider]:
        """Get all registered providers"""
        if not cls._initialized:
            cls.initialize()
        return cls._providers.copy()
    
    @classmethod
    def add_provider(cls, name: str, provider: BaseProvider):
        """Add a new provider to the registry"""
        cls._providers[name] = provider
        logger.info(f"✅ Added provider: {name}")
