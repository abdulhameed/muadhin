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

            # DISABLED: Twilio provider (using Africa's Talking exclusively)
            # Twilio was causing failures with account/number mismatch
            # Uncomment below if you need to re-enable Twilio
            # twilio_config = provider_configs.get('twilio', {
            #     'account_sid': getattr(settings, 'TWILIO_ACCOUNT_SID', ''),
            #     'auth_token': getattr(settings, 'TWILIO_AUTH_TOKEN', ''),
            #     'phone_number': getattr(settings, 'TWILIO_PHONE_NUMBER', ''),
            #     'whatsapp_number': getattr(settings, 'TWILIO_WHATSAPP_NUMBER', ''),
            #     'debug_mode': getattr(settings, 'DEBUG', True)
            # })
            #
            # if twilio_config.get('account_sid'):
            #     cls._providers['twilio'] = TwilioProvider(twilio_config)
            #     logger.info("✅ Twilio provider initialized")
            
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
            
            # Set up country preferences (OPTIMIZED for Africa with Africa's Talking)
            cls._country_preferences = {
                # AFRICA - Primary focus market with Africa's Talking
                'NG': ['africastalking'],       # Nigeria: Africa's Talking ONLY
                'KE': ['africastalking'],       # Kenya: AT home country
                'UG': ['africastalking'],       # Uganda: AT strong presence
                'TZ': ['africastalking'],       # Tanzania: AT coverage
                'RW': ['africastalking'],       # Rwanda: AT coverage
                'MW': ['africastalking'],       # Malawi: AT coverage
                'ZM': ['africastalking'],       # Zambia: AT coverage
                'GH': ['africastalking', 'nigeria'],  # Ghana: AT > Nigeria provider
                'CM': ['africastalking'],       # Cameroon: AT coverage
                'CI': ['africastalking'],       # Côte d'Ivoire: AT coverage
                'SN': ['africastalking'],       # Senegal: AT coverage
                'BF': ['africastalking'],       # Burkina Faso: AT coverage
                'ML': ['africastalking'],       # Mali: AT coverage
                'NE': ['africastalking'],       # Niger: AT coverage
                'TD': ['africastalking'],       # Chad: AT coverage

                # Asian countries - For future expansion
                'IN': ['india'],      # India: local provider
                'BD': ['india'],      # Bangladesh: can use India
                'LK': ['india'],      # Sri Lanka: can use India
                'NP': ['india'],      # Nepal: can use India

                # Other countries - will need provider setup in future
                # For now, they'll get Africa's Talking if available via fallback logic
                'GB': ['africastalking'],       # UK
                'CA': ['africastalking'],       # Canada
                'AU': ['africastalking'],       # Australia
                'AE': ['africastalking'],       # UAE
                'SA': ['africastalking'],       # Saudi Arabia
                'QA': ['africastalking'],       # Qatar
                'US': ['africastalking'],       # USA
                'DE': ['africastalking'],       # Germany
                'FR': ['africastalking'],       # France
            }
            
            cls._initialized = True
            logger.info(f"✅ Provider registry initialized with {len(cls._providers)} providers")
            
        except Exception as e:
            logger.error(f"❌ Error initializing provider registry: {e}")
            # DISABLED: Twilio fallback (using Africa's Talking exclusively)
            # if 'twilio' not in cls._providers:
            #     cls._providers['twilio'] = TwilioProvider({'debug_mode': True})

    
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
            ['africastalking']  # Default to Africa's Talking
        )
        
        providers = []
        for name in provider_names:
            provider = cls._providers.get(name)
            if provider and provider.is_configured:
                providers.append(provider)

        # Fallback to Africa's Talking if no providers were found
        if not providers:
            at_provider = cls._providers.get('africastalking')
            if at_provider and at_provider.is_configured:
                providers.append(at_provider)

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
    
    @classmethod
    def get_cost_estimate_for_country(cls, country_code: str, message_count: int = 1) -> dict:
        """Get cost estimate for sending messages to a country"""
        if not cls._initialized:
            cls.initialize()
        
        providers = cls.get_providers_for_country(country_code)
        estimates = {}
        
        for provider in providers:
            if hasattr(provider, 'get_cost_per_message'):
                cost_per_msg = provider.get_cost_per_message(country_code)
                total_cost = cost_per_msg * message_count
                estimates[provider.name] = {
                    'cost_per_message': cost_per_msg,
                    'total_cost': total_cost,
                    'currency': 'USD'
                }
        
        return estimates
    
    @classmethod
    def get_best_provider_for_cost(cls, country_code: str) -> Optional[BaseProvider]:
        """Get the cheapest provider for a country"""
        providers = cls.get_providers_for_country(country_code)
        
        if not providers:
            return None
        
        best_provider = None
        lowest_cost = float('inf')
        
        for provider in providers:
            if hasattr(provider, 'get_cost_per_message'):
                cost = provider.get_cost_per_message(country_code)
                if cost < lowest_cost:
                    lowest_cost = cost
                    best_provider = provider
        
        return best_provider or providers[0]  # Return first if no cost info available
