from typing import Optional, List
from django.contrib.auth import get_user_model
import logging

from .provider_registry import ProviderRegistry
from ..providers.base import CommunicationResult, SMSProvider, CallProvider, WhatsAppProvider
from subscriptions.models import NotificationUsage

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Main service for sending notifications with automatic provider selection"""
    
    @staticmethod
    def send_sms(user, message: str, log_usage: bool = True) -> CommunicationResult:
        """Send SMS using the best available provider for user's country"""
        country_code = getattr(user, 'country', 'US')[:2].upper()
        phone_number = getattr(user, 'phone_number', '')
        
        if not phone_number:
            return CommunicationResult(
                success=False,
                error_message="No phone number provided",
                provider_name="NotificationService"
            )
        
        providers = ProviderRegistry.get_providers_for_country(country_code)
        sms_providers = [p for p in providers if isinstance(p, SMSProvider)]
        
        if not sms_providers:
            return CommunicationResult(
                success=False,
                error_message="No SMS providers available",
                provider_name="NotificationService"
            )
        
        # Try providers in order of preference
        last_error = None
        for provider in sms_providers:
            try:
                result = provider.send_sms_sync(phone_number, message, country_code)
                
                if result.success:
                    logger.info(f"✅ SMS sent via {provider.name} to {phone_number[:8]}***")
                    
                    # Log usage if requested
                    if log_usage:
                        NotificationService._log_usage(
                            user, 'sms', result.provider_name, 
                            True, result.message_id, result.cost
                        )
                    
                    return result
                else:
                    last_error = result.error_message
                    logger.warning(f"⚠️ SMS failed via {provider.name}: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ SMS provider {provider.name} error: {e}")
                continue
        
        # All providers failed
        error_result = CommunicationResult(
            success=False,
            error_message=f"All SMS providers failed. Last error: {last_error}",
            provider_name="NotificationService"
        )
        
        if log_usage:
            NotificationService._log_usage(
                user, 'sms', 'failed', False, 
                error_message=error_result.error_message
            )
        
        return error_result
    
    @staticmethod
    def make_call(user, audio_url: str, log_usage: bool = True) -> CommunicationResult:
        """Make voice call using the best available provider"""
        country_code = getattr(user, 'country', 'US')[:2].upper()
        phone_number = getattr(user, 'phone_number', '')
        
        if not phone_number:
            return CommunicationResult(
                success=False,
                error_message="No phone number provided",
                provider_name="NotificationService"
            )
        
        providers = ProviderRegistry.get_providers_for_country(country_code)
        call_providers = [p for p in providers if isinstance(p, CallProvider)]
        
        if not call_providers:
            return CommunicationResult(
                success=False,
                error_message="No call providers available",
                provider_name="NotificationService"
            )
        
        # Try providers in order of preference
        last_error = None
        for provider in call_providers:
            try:
                result = provider.make_call_sync(phone_number, audio_url, country_code)
                
                if result.success:
                    logger.info(f"✅ Call made via {provider.name} to {phone_number[:8]}***")
                    
                    if log_usage:
                        NotificationService._log_usage(
                            user, 'call', result.provider_name,
                            True, result.message_id, result.cost
                        )
                    
                    return result
                else:
                    last_error = result.error_message
                    logger.warning(f"⚠️ Call failed via {provider.name}: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ Call provider {provider.name} error: {e}")
                continue
        
        # All providers failed
        error_result = CommunicationResult(
            success=False,
            error_message=f"All call providers failed. Last error: {last_error}",
            provider_name="NotificationService"
        )
        
        if log_usage:
            NotificationService._log_usage(
                user, 'call', 'failed', False,
                error_message=error_result.error_message
            )
        
        return error_result
    
    @staticmethod
    def make_text_call(user, text_message: str, log_usage: bool = True) -> CommunicationResult:
        """Make text-to-speech call using the best available provider"""
        country_code = getattr(user, 'country', 'US')[:2].upper()
        phone_number = getattr(user, 'phone_number', '')
        
        if not phone_number:
            return CommunicationResult(
                success=False,
                error_message="No phone number provided",
                provider_name="NotificationService"
            )
        
        providers = ProviderRegistry.get_providers_for_country(country_code)
        call_providers = [p for p in providers if isinstance(p, CallProvider)]
        
        if not call_providers:
            # Fallback to SMS if no call providers
            return NotificationService.send_sms(user, f"🔊 {text_message}", log_usage)
        
        # Try providers in order of preference
        last_error = None
        for provider in call_providers:
            try:
                result = provider.make_text_call_sync(phone_number, text_message, country_code)
                
                if result.success:
                    logger.info(f"✅ Text call made via {provider.name} to {phone_number[:8]}***")
                    
                    if log_usage:
                        NotificationService._log_usage(
                            user, 'call', result.provider_name,
                            True, result.message_id, result.cost
                        )
                    
                    return result
                else:
                    last_error = result.error_message
                    logger.warning(f"⚠️ Text call failed via {provider.name}: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ Text call provider {provider.name} error: {e}")
                continue
        
        # All providers failed, fallback to SMS
        logger.info("📱 Text call failed, falling back to SMS")
        return NotificationService.send_sms(user, f"🔊 {text_message}", log_usage)
    
    @staticmethod
    def send_whatsapp(user, message: str, log_usage: bool = True) -> CommunicationResult:
        """Send WhatsApp message using the best available provider"""
        country_code = getattr(user, 'country', 'US')[:2].upper()
        whatsapp_number = getattr(user, 'whatsapp_number', '') or getattr(user, 'phone_number', '')
        
        if not whatsapp_number:
            return CommunicationResult(
                success=False,
                error_message="No WhatsApp number provided",
                provider_name="NotificationService"
            )
        
        providers = ProviderRegistry.get_providers_for_country(country_code)
        whatsapp_providers = [p for p in providers if isinstance(p, WhatsAppProvider)]
        
        if not whatsapp_providers:
            # Fallback to SMS if no WhatsApp providers
            return NotificationService.send_sms(user, f"💬 {message}", log_usage)
        
        # Try providers in order of preference
        last_error = None
        for provider in whatsapp_providers:
            try:
                result = provider.send_whatsapp_sync(whatsapp_number, message, country_code)
                
                if result.success:
                    logger.info(f"✅ WhatsApp sent via {provider.name} to {whatsapp_number[:8]}***")
                    
                    if log_usage:
                        NotificationService._log_usage(
                            user, 'whatsapp', result.provider_name,
                            True, result.message_id, result.cost
                        )
                    
                    return result
                else:
                    last_error = result.error_message
                    logger.warning(f"⚠️ WhatsApp failed via {provider.name}: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ WhatsApp provider {provider.name} error: {e}")
                continue
        
        # All WhatsApp providers failed, fallback to SMS
        logger.info("📱 WhatsApp failed, falling back to SMS")
        return NotificationService.send_sms(user, f"💬 {message}", log_usage)
    
    @staticmethod
    def _log_usage(user, notification_type: str, provider_name: str, 
                   success: bool, message_id: str = None, cost: float = None,
                   error_message: str = None):
        """Log notification usage for analytics and billing"""
        try:
            NotificationUsage.objects.create(
                user=user,
                notification_type=notification_type,
                success=success,
                error_message=error_message,
            )
        except Exception as e:
            logger.error(f"Failed to log notification usage: {e}")
    
    @staticmethod
    def get_provider_status(country_code: str = None) -> dict:
        """Get status of all providers for a country"""
        providers = ProviderRegistry.get_providers_for_country(country_code or 'US')
        
        status = {
            'country_code': country_code,
            'available_providers': len(providers),
            'providers': []
        }
        
        for provider in providers:
            status['providers'].append({
                'name': provider.name,
                'configured': provider.is_configured,
                'supported_countries': provider.get_supported_countries(),
                'cost_estimate': provider.get_cost_per_message(country_code or 'US')
            })
        
        return status
