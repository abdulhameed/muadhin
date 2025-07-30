from .base import CombinedProvider, CommunicationResult
from typing import Dict, Any
import logging
import requests

logger = logging.getLogger(__name__)


class IndiaProvider(CombinedProvider):
    """Cost-effective provider for India using local services"""
    
    def _validate_config(self) -> bool:
        """Validate India provider configuration"""
        # Example for Indian SMS services like TextLocal, MSG91, etc.
        required_keys = ['api_key', 'sender_id']
        return all(key in self.config for key in required_keys)
    
    def get_supported_countries(self) -> list:
        """Supports India and nearby countries"""
        return ['IN', 'BD', 'LK', 'NP']  # India, Bangladesh, Sri Lanka, Nepal
    
    def get_cost_per_message(self, country_code: str) -> float:
        """Very cheap costs for India"""
        cost_map = {
            'IN': 0.008,  # India - $0.008 per SMS (much cheaper than Twilio)
            'BD': 0.012,  # Bangladesh
            'LK': 0.015,  # Sri Lanka
            'NP': 0.010,  # Nepal
        }
        return cost_map.get(country_code.upper(), 0.01)
    
    async def send_sms(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send SMS via Indian provider (e.g., TextLocal, MSG91)"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'IN')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[INDIA DEBUG] SMS to {formatted_number}: {message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"india_debug_{hash(formatted_number)}",
                    provider_name="IndiaProvider",
                    cost=self.get_cost_per_message(country_code or 'IN')
                )
            
            # Example API call to an Indian SMS service
            api_url = self.config.get('api_url', 'https://api.textlocal.in/send/')
            
            payload = {
                'apikey': self.config['api_key'],
                'numbers': formatted_number.replace('+91', ''),
                'message': message,
                'sender': self.config.get('sender_id', 'MUADHN')
            }
            
            response = requests.post(api_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    return CommunicationResult(
                        success=True,
                        message_id=result.get('batch_id', str(hash(formatted_number))),
                        provider_name="IndiaProvider",
                        cost=self.get_cost_per_message(country_code or 'IN'),
                        raw_response=result
                    )
                else:
                    raise Exception(f"API error: {result.get('errors', 'Unknown error')}")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"India SMS failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="IndiaProvider"
            )
    
    async def make_call(self, to_number: str, audio_url: str, country_code: str = None) -> CommunicationResult:
        """Voice calls using Indian provider"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'IN')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[INDIA DEBUG] Call to {formatted_number} with audio: {audio_url}")
                return CommunicationResult(
                    success=True,
                    message_id=f"india_call_debug_{hash(formatted_number)}",
                    provider_name="IndiaProvider",
                    cost=self.get_cost_per_message(country_code or 'IN') * 6
                )
            
            # Many Indian providers have voice call APIs
            # Implement based on chosen provider (Exotel, Knowlarity, etc.)
            # For now, fallback to SMS
            sms_message = "🕌 Adhan - Prayer time! Please prepare for Salah."
            return await self.send_sms(formatted_number, sms_message, country_code)
            
        except Exception as e:
            logger.error(f"India call failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="IndiaProvider"
            )
    
    async def make_text_call(self, to_number: str, text_message: str, country_code: str = None) -> CommunicationResult:
        """Text-to-speech calls - fallback to SMS for now"""
        return await self.send_sms(to_number, f"🔊 {text_message}", country_code)
    
    async def send_whatsapp(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """WhatsApp via Indian provider (if supported) or fallback to SMS"""
        # Some Indian providers support WhatsApp Business API
        # For now, fallback to SMS with special formatting
        whatsapp_message = f"💬 WhatsApp Message: {message}"
        return await self.send_sms(to_number, whatsapp_message, country_code)