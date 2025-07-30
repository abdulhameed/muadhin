from .base import CombinedProvider, CommunicationResult
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TwilioProvider(CombinedProvider):
    """Twilio provider - serves as universal fallback"""
    
    def _validate_config(self) -> bool:
        """Validate Twilio configuration"""
        required_keys = ['account_sid', 'auth_token', 'phone_number']
        return all(key in self.config for key in required_keys)
    
    def get_supported_countries(self) -> list:
        """Twilio supports most countries worldwide"""
        return ['*']  # Universal fallback
    
    def get_cost_per_message(self, country_code: str) -> float:
        """Return cost per message for given country"""
        # Twilio pricing varies by country
        cost_map = {
            'NG': 0.035,  # Nigeria - $0.035 per SMS
            'IN': 0.0063,  # India - $0.0063 per SMS
            'US': 0.0075,  # USA - $0.0075 per SMS
            'GB': 0.041,   # UK - $0.041 per SMS
        }
        return cost_map.get(country_code.upper(), 0.05)  # Default $0.05
    
    async def send_sms(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.config['account_sid'], self.config['auth_token'])
            formatted_number = self.format_phone_number(to_number, country_code or 'US')
            
            # For development/testing, just log instead of actually sending
            if self.config.get('debug_mode', False):
                logger.info(f"[TWILIO DEBUG] SMS to {formatted_number}: {message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"twilio_debug_{hash(formatted_number)}",
                    provider_name="TwilioProvider",
                    cost=self.get_cost_per_message(country_code or 'US')
                )
            
            twilio_message = client.messages.create(
                body=message,
                from_=self.config['phone_number'],
                to=formatted_number
            )
            
            return CommunicationResult(
                success=True,
                message_id=twilio_message.sid,
                provider_name="TwilioProvider",
                cost=self.get_cost_per_message(country_code or 'US'),
                delivery_status=twilio_message.status,
                raw_response={'sid': twilio_message.sid, 'status': twilio_message.status}
            )
            
        except Exception as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="TwilioProvider"
            )
    
    async def make_call(self, to_number: str, audio_url: str, country_code: str = None) -> CommunicationResult:
        """Make voice call via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.config['account_sid'], self.config['auth_token'])
            formatted_number = self.format_phone_number(to_number, country_code or 'US')
            
            # For development/testing, just log instead of actually calling
            if self.config.get('debug_mode', False):
                logger.info(f"[TWILIO DEBUG] Call to {formatted_number} with audio: {audio_url}")
                return CommunicationResult(
                    success=True,
                    message_id=f"twilio_call_debug_{hash(formatted_number)}",
                    provider_name="TwilioProvider",
                    cost=self.get_cost_per_message(country_code or 'US') * 10  # Calls are more expensive
                )
            
            call = client.calls.create(
                twiml=f'<Response><Play>{audio_url}</Play></Response>',
                to=formatted_number,
                from_=self.config['phone_number']
            )
            
            return CommunicationResult(
                success=True,
                message_id=call.sid,
                provider_name="TwilioProvider",
                cost=self.get_cost_per_message(country_code or 'US') * 10,
                delivery_status=call.status,
                raw_response={'sid': call.sid, 'status': call.status}
            )
            
        except Exception as e:
            logger.error(f"Twilio call failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="TwilioProvider"
            )
    
    async def make_text_call(self, to_number: str, text_message: str, country_code: str = None) -> CommunicationResult:
        """Make text-to-speech call via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.config['account_sid'], self.config['auth_token'])
            formatted_number = self.format_phone_number(to_number, country_code or 'US')
            
            # For development/testing, just log instead of actually calling
            if self.config.get('debug_mode', False):
                logger.info(f"[TWILIO DEBUG] Text call to {formatted_number}: {text_message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"twilio_text_call_debug_{hash(formatted_number)}",
                    provider_name="TwilioProvider",
                    cost=self.get_cost_per_message(country_code or 'US') * 8
                )
            
            call = client.calls.create(
                twiml=f'<Response><Say>{text_message}</Say></Response>',
                to=formatted_number,
                from_=self.config['phone_number']
            )
            
            return CommunicationResult(
                success=True,
                message_id=call.sid,
                provider_name="TwilioProvider",
                cost=self.get_cost_per_message(country_code or 'US') * 8,
                delivery_status=call.status,
                raw_response={'sid': call.sid, 'status': call.status}
            )
            
        except Exception as e:
            logger.error(f"Twilio text call failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="TwilioProvider"
            )
    
    async def send_whatsapp(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send WhatsApp message via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.config['account_sid'], self.config['auth_token'])
            formatted_number = self.format_phone_number(to_number, country_code or 'US')
            
            # For development/testing, just log instead of actually sending
            if self.config.get('debug_mode', False):
                logger.info(f"[TWILIO DEBUG] WhatsApp to {formatted_number}: {message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"twilio_whatsapp_debug_{hash(formatted_number)}",
                    provider_name="TwilioProvider",
                    cost=self.get_cost_per_message(country_code or 'US') * 1.5
                )
            
            twilio_message = client.messages.create(
                from_=f"whatsapp:{self.config.get('whatsapp_number', self.config['phone_number'])}",
                body=message,
                to=f"whatsapp:{formatted_number}"
            )
            
            return CommunicationResult(
                success=True,
                message_id=twilio_message.sid,
                provider_name="TwilioProvider",
                cost=self.get_cost_per_message(country_code or 'US') * 1.5,
                delivery_status=twilio_message.status,
                raw_response={'sid': twilio_message.sid, 'status': twilio_message.status}
            )
            
        except Exception as e:
            logger.error(f"Twilio WhatsApp failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="TwilioProvider"
            )
