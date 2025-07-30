from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CommunicationResult:
    """Standard result format for all communication attempts"""
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    provider_name: str = ""
    cost: Optional[float] = None
    delivery_status: str = "unknown"
    raw_response: Optional[Dict] = None
    
    def to_dict(self):
        return {
            'success': self.success,
            'message_id': self.message_id,
            'error_message': self.error_message,
            'provider_name': self.provider_name,
            'cost': self.cost,
            'delivery_status': self.delivery_status
        }


class BaseProvider(ABC):
    """Base class for all communication providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        self.is_configured = self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> bool:
        """Validate provider configuration"""
        pass
    
    @abstractmethod
    def get_supported_countries(self) -> list:
        """Return list of ISO country codes this provider supports"""
        pass
    
    @abstractmethod
    def get_cost_per_message(self, country_code: str) -> float:
        """Return cost per message for given country"""
        pass
    
    def format_phone_number(self, phone_number: str, country_code: str) -> str:
        """Format phone number for this provider"""
        if not phone_number.startswith('+'):
            # Add country-specific formatting logic here
            if country_code.upper() == 'NG':  # Nigeria
                if phone_number.startswith('0'):
                    phone_number = '+234' + phone_number[1:]
                elif not phone_number.startswith('+234'):
                    phone_number = '+234' + phone_number
            elif country_code.upper() == 'IN':  # India
                if not phone_number.startswith('+91'):
                    phone_number = '+91' + phone_number
            else:
                # Default formatting
                phone_number = '+' + phone_number.lstrip('+')
        
        return phone_number


class SMSProvider(BaseProvider):
    """Abstract base class for SMS providers"""
    
    @abstractmethod
    async def send_sms(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send SMS message"""
        pass
    
    def send_sms_sync(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Synchronous wrapper for send_sms"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.send_sms(to_number, message, country_code))


class CallProvider(BaseProvider):
    """Abstract base class for voice call providers"""
    
    @abstractmethod
    async def make_call(self, to_number: str, audio_url: str, country_code: str = None) -> CommunicationResult:
        """Make voice call with audio"""
        pass
    
    @abstractmethod
    async def make_text_call(self, to_number: str, text_message: str, country_code: str = None) -> CommunicationResult:
        """Make voice call with text-to-speech"""
        pass
    
    def make_call_sync(self, to_number: str, audio_url: str, country_code: str = None) -> CommunicationResult:
        """Synchronous wrapper for make_call"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.make_call(to_number, audio_url, country_code))
    
    def make_text_call_sync(self, to_number: str, text_message: str, country_code: str = None) -> CommunicationResult:
        """Synchronous wrapper for make_text_call"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.make_text_call(to_number, text_message, country_code))


class WhatsAppProvider(BaseProvider):
    """Abstract base class for WhatsApp providers"""
    
    @abstractmethod
    async def send_whatsapp(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send WhatsApp message"""
        pass
    
    def send_whatsapp_sync(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Synchronous wrapper for send_whatsapp"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.send_whatsapp(to_number, message, country_code))


class CombinedProvider(SMSProvider, CallProvider, WhatsAppProvider):
    """Provider that supports SMS, calls, and WhatsApp"""
    pass
