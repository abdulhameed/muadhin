from .base import CombinedProvider, CommunicationResult
from typing import Dict, Any
import logging
import requests

logger = logging.getLogger(__name__)


class NigeriaProvider(CombinedProvider):
    """Cost-effective provider for Nigeria using local services"""
    
    def _validate_config(self) -> bool:
        """Validate Nigeria provider configuration"""
        # Example for a Nigerian SMS service like TermiiSMS, BulkSMSNigeria etc.
        required_keys = ['api_key', 'sender_id']
        return all(key in self.config for key in required_keys)
    
    def get_supported_countries(self) -> list:
        """Supports Nigeria primarily"""
        return ['NG', 'GH', 'BJ']  # Nigeria, Ghana, Benin
    
    def get_cost_per_message(self, country_code: str) -> float:
        """Much cheaper costs for Nigeria"""
        cost_map = {
            'NG': 0.015,  # Nigeria - $0.015 per SMS (much cheaper than Twilio)
            'GH': 0.025,  # Ghana
            'BJ': 0.020,  # Benin
        }
        return cost_map.get(country_code.upper(), 0.02)
    
    async def send_sms(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send SMS via Nigerian provider (e.g., Termii, BulkSMS Nigeria)"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'NG')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[NIGERIA DEBUG] SMS to {formatted_number}: {message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"nigeria_debug_{hash(formatted_number)}",
                    provider_name="NigeriaProvider",
                    cost=self.get_cost_per_message(country_code or 'NG')
                )
            
            # Example API call to a Nigerian SMS service
            api_url = self.config.get('api_url', 'https://api.termii.com/api/sms/send')
            
            payload = {
                "to": formatted_number.replace('+', ''),
                "from": self.config.get('sender_id', 'Muadhin'),
                "sms": message,
                "type": "plain",
                "api_key": self.config['api_key'],
                "channel": "generic"
            }
            
            response = requests.post(api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return CommunicationResult(
                    success=True,
                    message_id=result.get('message_id', str(hash(formatted_number))),
                    provider_name="NigeriaProvider",
                    cost=self.get_cost_per_message(country_code or 'NG'),
                    raw_response=result
                )
            else:
                raise Exception(f"API returned {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Nigeria SMS failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="NigeriaProvider"
            )
    
    async def make_call(self, to_number: str, audio_url: str, country_code: str = None) -> CommunicationResult:
        """Voice calls using Nigerian provider"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'NG')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[NIGERIA DEBUG] Call to {formatted_number} with audio: {audio_url}")
                return CommunicationResult(
                    success=True,
                    message_id=f"nigeria_call_debug_{hash(formatted_number)}",
                    provider_name="NigeriaProvider",
                    cost=self.get_cost_per_message(country_code or 'NG') * 5
                )
            
            # Many Nigerian providers don't support voice calls yet
            # Fall back to SMS for now or implement when available
            sms_message = "🕌 Adhan - It's time for prayer! Allahu Akbar!"
            return await self.send_sms(formatted_number, sms_message, country_code)
            
        except Exception as e:
            logger.error(f"Nigeria call failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="NigeriaProvider"
            )
    
    async def make_text_call(self, to_number: str, text_message: str, country_code: str = None) -> CommunicationResult:
        """Text-to-speech calls - fallback to SMS for now"""
        return await self.send_sms(to_number, f"🔔 {text_message}", country_code)
    
    async def send_whatsapp(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """WhatsApp via Nigerian provider (if supported) or fallback to SMS"""
        # Most local providers don't support WhatsApp yet
        # Fallback to SMS with WhatsApp-style formatting
        whatsapp_message = f"📱 WhatsApp: {message}"
        return await self.send_sms(to_number, whatsapp_message, country_code)
