from typing import Dict, List, Optional, Type
from django.conf import settings
import logging

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
            
            # Initialize Nigeria provider
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
            
            # Set up country preferences (which provider to try first for each country)
            cls._country_preferences = {
                'NG': ['nigeria', 'twilio'],  # Nigeria: try local first, then Twilio
                'GH': ['nigeria', 'twilio'],  # Ghana: can use Nigeria provider
                'IN': ['india', 'twilio'],    # India: try local first, then Twilio
                'BD': ['india', 'twilio'],    # Bangladesh: can use India provider
                'US': ['twilio'],             # USA: Twilio only
                'GB': ['twilio'],             # UK: Twilio only
                'CA': ['twilio'],             # Canada: Twilio only
                # Add more countries as needed
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
