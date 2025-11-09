from .base import CombinedProvider, CommunicationResult
from typing import Dict, Any
import logging
import requests
import json

logger = logging.getLogger(__name__)


class AfricasTalkingProvider(CombinedProvider):
    """
    Africa's Talking provider for African countries - excellent for voice calls and SMS
    Supports Nigeria, Kenya, Uganda, Tanzania, Rwanda, Malawi, and other African countries
    """
    
    def _validate_config(self) -> bool:
        """Validate Africa's Talking configuration"""
        required_keys = ['username', 'api_key']
        return all(key in self.config for key in required_keys)
    
    def get_supported_countries(self) -> list:
        """Africa's Talking supports multiple African countries"""
        return [
            'NG',  # Nigeria
            'KE',  # Kenya
            'UG',  # Uganda
            'TZ',  # Tanzania
            'RW',  # Rwanda
            'MW',  # Malawi
            'ZM',  # Zambia
            'GH',  # Ghana
            'CM',  # Cameroon
            'CI',  # Côte d'Ivoire
            'SN',  # Senegal
            'BF',  # Burkina Faso
            'ML',  # Mali
            'NE',  # Niger
            'TD',  # Chad
        ]
    
    def get_cost_per_message(self, country_code: str) -> float:
        """Africa's Talking competitive costs for African countries"""
        cost_map = {
            'NG': 0.012,  # Nigeria - Very competitive
            'KE': 0.010,  # Kenya - Home country, cheapest
            'UG': 0.011,  # Uganda
            'TZ': 0.013,  # Tanzania
            'RW': 0.015,  # Rwanda
            'MW': 0.018,  # Malawi
            'ZM': 0.016,  # Zambia
            'GH': 0.014,  # Ghana
            'CM': 0.020,  # Cameroon
            'CI': 0.022,  # Côte d'Ivoire
            'SN': 0.021,  # Senegal
            'BF': 0.025,  # Burkina Faso
            'ML': 0.024,  # Mali
            'NE': 0.023,  # Niger
            'TD': 0.026,  # Chad
        }
        return cost_map.get(country_code.upper(), 0.02)
    
    def get_voice_cost_per_minute(self, country_code: str) -> float:
        """Voice call costs per minute (much cheaper than Twilio for Africa)"""
        voice_cost_map = {
            'NG': 0.05,   # Nigeria - $0.05/minute vs Twilio $0.85/minute
            'KE': 0.04,   # Kenya - $0.04/minute
            'UG': 0.06,   # Uganda
            'TZ': 0.07,   # Tanzania
            'RW': 0.08,   # Rwanda
            'MW': 0.09,   # Malawi
            'ZM': 0.08,   # Zambia
            'GH': 0.06,   # Ghana
        }
        return voice_cost_map.get(country_code.upper(), 0.08)
    
    async def send_sms(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """Send SMS via Africa's Talking"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'NG')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[AFRICAS_TALKING DEBUG] SMS to {formatted_number}: {message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"at_sms_debug_{hash(formatted_number)}",
                    provider_name="AfricasTalkingProvider",
                    cost=self.get_cost_per_message(country_code or 'NG')
                )
            
            # Africa's Talking SMS API
            api_url = "https://api.africastalking.com/version1/messaging"
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'apiKey': self.config['api_key']
            }
            
            # Remove + from phone number for Africa's Talking
            clean_number = formatted_number.replace('+', '')
            
            payload = {
                'username': self.config['username'],
                'to': clean_number,
                'message': message
            }
            
            # Only add sender_id if explicitly configured and not empty
            sender_id = self.config.get('sender_id')
            if sender_id and sender_id.strip():
                payload['from'] = sender_id
            
            response = requests.post(api_url, headers=headers, data=payload, timeout=30)
            
            if response.status_code == 201:
                result = response.json()
                sms_message_data = result['SMSMessageData']
                recipients = sms_message_data['Recipients']
                
                if recipients and len(recipients) > 0:
                    recipient = recipients[0]
                    if recipient['status'] == 'Success':
                        return CommunicationResult(
                            success=True,
                            message_id=recipient.get('messageId', str(hash(formatted_number))),
                            provider_name="AfricasTalkingProvider",
                            cost=self.get_cost_per_message(country_code or 'NG'),
                            delivery_status='sent',
                            raw_response=result
                        )
                    else:
                        raise Exception(f"SMS failed: {recipient.get('status', 'Unknown error')}")
                else:
                    raise Exception("No recipients in response")
            else:
                raise Exception(f"API returned {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Africa's Talking SMS failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="AfricasTalkingProvider"
            )
    
    async def make_call(self, to_number: str, audio_url: str, country_code: str = None) -> CommunicationResult:
        """Make voice call with audio file via Africa's Talking"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'NG')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[AFRICAS_TALKING DEBUG] Call to {formatted_number} with audio: {audio_url}")
                return CommunicationResult(
                    success=True,
                    message_id=f"at_call_debug_{hash(formatted_number)}",
                    provider_name="AfricasTalkingProvider",
                    cost=self.get_voice_cost_per_minute(country_code or 'NG') * 2  # Assume 2 min call
                )
            
            # Africa's Talking Voice API
            api_url = "https://voice.africastalking.com/call"
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'apiKey': self.config['api_key']
            }
            
            # Remove + from phone number
            clean_number = formatted_number.replace('+', '')

            # Store audio URL in database for callback to retrieve
            # AT strips query params, so we use database with phone number as key
            from communications.models import VoiceCallSession
            from asgiref.sync import sync_to_async

            # Create session in sync context
            await sync_to_async(VoiceCallSession.objects.create)(
                phone_number=formatted_number,
                call_type='adhan_audio',
                audio_url=audio_url
            )

            # Don't send callbackUrl in API request - use dashboard setting instead
            # Africa's Talking rejects custom callback URLs in API requests

            payload = {
                'username': self.config['username'],
                'to': clean_number,
                'from': self.config.get('caller_id', self.config.get('phone_number', '+254711XXXXXX'))
            }

            logger.info(f"🔔 Making AT voice call to {clean_number}:")
            logger.info(f"   Using dashboard callback URL (not sent in API request)")
            logger.info(f"   Audio URL stored in DB: {audio_url}")
            logger.info(f"   Phone number: {formatted_number}")

            response = requests.post(api_url, headers=headers, data=payload, timeout=30)

            logger.info(f"📥 AT Response: {response.status_code} - {response.text[:200]}")
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                
                # Africa's Talking returns different structure for voice
                if 'entries' in result and len(result['entries']) > 0:
                    call_entry = result['entries'][0]
                    if call_entry.get('status') == 'Queued':
                        return CommunicationResult(
                            success=True,
                            message_id=call_entry.get('phoneNumber', str(hash(formatted_number))),
                            provider_name="AfricasTalkingProvider",
                            cost=self.get_voice_cost_per_minute(country_code or 'NG') * 2,
                            delivery_status='queued',
                            raw_response=result
                        )
                    else:
                        raise Exception(f"Call failed: {call_entry.get('status', 'Unknown error')}")
                else:
                    # Sometimes AT returns success without detailed entries
                    return CommunicationResult(
                        success=True,
                        message_id=f"at_call_{hash(formatted_number)}",
                        provider_name="AfricasTalkingProvider",
                        cost=self.get_voice_cost_per_minute(country_code or 'NG') * 2,
                        delivery_status='initiated',
                        raw_response=result
                    )
            else:
                raise Exception(f"Voice API returned {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Africa's Talking call failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="AfricasTalkingProvider"
            )
    
    async def make_text_call(self, to_number: str, text_message: str, country_code: str = None) -> CommunicationResult:
        """Make text-to-speech call via Africa's Talking"""
        try:
            formatted_number = self.format_phone_number(to_number, country_code or 'NG')
            
            # For development/testing
            if self.config.get('debug_mode', False):
                logger.info(f"[AFRICAS_TALKING DEBUG] TTS Call to {formatted_number}: {text_message}")
                return CommunicationResult(
                    success=True,
                    message_id=f"at_tts_debug_{hash(formatted_number)}",
                    provider_name="AfricasTalkingProvider",
                    cost=self.get_voice_cost_per_minute(country_code or 'NG') * 1.5  # Assume 1.5 min call
                )
            
            # Africa's Talking Voice API with TTS
            api_url = "https://voice.africastalking.com/call"
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'apiKey': self.config['api_key']
            }
            
            # Remove + from phone number
            clean_number = formatted_number.replace('+', '')

            # Store TTS message in database for callback to retrieve
            from communications.models import VoiceCallSession
            from asgiref.sync import sync_to_async

            # Create session in sync context
            await sync_to_async(VoiceCallSession.objects.create)(
                phone_number=formatted_number,
                call_type='tts',
                message=text_message
            )

            # Don't send callbackUrl in API request - use dashboard setting instead

            payload = {
                'username': self.config['username'],
                'to': clean_number,
                'from': self.config.get('caller_id', self.config.get('phone_number', '+254711XXXXXX'))
            }
            
            response = requests.post(api_url, headers=headers, data=payload, timeout=30)
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                
                if 'entries' in result and len(result['entries']) > 0:
                    call_entry = result['entries'][0]
                    return CommunicationResult(
                        success=True,
                        message_id=call_entry.get('phoneNumber', str(hash(formatted_number))),
                        provider_name="AfricasTalkingProvider",
                        cost=self.get_voice_cost_per_minute(country_code or 'NG') * 1.5,
                        delivery_status=call_entry.get('status', 'queued'),
                        raw_response=result
                    )
                else:
                    return CommunicationResult(
                        success=True,
                        message_id=f"at_tts_{hash(formatted_number)}",
                        provider_name="AfricasTalkingProvider",
                        cost=self.get_voice_cost_per_minute(country_code or 'NG') * 1.5,
                        delivery_status='initiated',
                        raw_response=result
                    )
            else:
                raise Exception(f"TTS API returned {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Africa's Talking TTS call failed: {str(e)}")
            return CommunicationResult(
                success=False,
                error_message=str(e),
                provider_name="AfricasTalkingProvider"
            )
    
    async def send_whatsapp(self, to_number: str, message: str, country_code: str = None) -> CommunicationResult:
        """
        Africa's Talking doesn't directly support WhatsApp yet
        Fall back to SMS with WhatsApp-style formatting
        """
        whatsapp_message = f"📱 WhatsApp Message: {message}"
        return await self.send_sms(to_number, whatsapp_message, country_code)
    
    def format_phone_number(self, phone_number: str, country_code: str) -> str:
        """Format phone number for Africa's Talking (they prefer without + for some APIs)"""
        if not phone_number.startswith('+'):
            # Add country-specific formatting
            if country_code.upper() == 'NG':  # Nigeria
                if phone_number.startswith('0'):
                    phone_number = '+234' + phone_number[1:]
                elif not phone_number.startswith('+234'):
                    phone_number = '+234' + phone_number
            elif country_code.upper() == 'KE':  # Kenya
                if phone_number.startswith('0'):
                    phone_number = '+254' + phone_number[1:]
                elif not phone_number.startswith('+254'):
                    phone_number = '+254' + phone_number
            elif country_code.upper() == 'UG':  # Uganda
                if phone_number.startswith('0'):
                    phone_number = '+256' + phone_number[1:]
                elif not phone_number.startswith('+256'):
                    phone_number = '+256' + phone_number
            elif country_code.upper() == 'TZ':  # Tanzania
                if phone_number.startswith('0'):
                    phone_number = '+255' + phone_number[1:]
                elif not phone_number.startswith('+255'):
                    phone_number = '+255' + phone_number
            else:
                # Default: add + if not present
                phone_number = '+' + phone_number.lstrip('+')
        
        return phone_number
