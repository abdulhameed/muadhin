from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp messages via Twilio"""
    
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
    
    def send_message(self, to_number, message):
        """Send a WhatsApp message"""
        try:
            # Ensure the number includes country code and is properly formatted
            if not to_number.startswith('+'):
                to_number = f'+{to_number}'
            
            to_whatsapp = f"whatsapp:{to_number}"
            
            message = self.client.messages.create(
                from_=self.from_number,
                body=message,
                to=to_whatsapp
            )
            
            logger.info(f"WhatsApp message sent successfully. SID: {message.sid}")
            return message.sid
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}")
            raise
    
    def send_daily_prayer_summary(self, user, prayer_times):
        """Send daily prayer summary via WhatsApp"""
        message = f"🕌 Assalamu Alaikum, {user.username}!\n\n"
        message += "Today's prayer times:\n"
        
        for prayer_time in prayer_times:
            message += f"• {prayer_time.prayer_name}: {prayer_time.prayer_time.strftime('%I:%M %p')}\n"
        
        message += "\n📱 You'll receive reminders before each prayer time."
        
        return self.send_message(user.whatsapp_number, message)
    
    def send_pre_adhan_notification(self, user, prayer_name, prayer_time):
        """Send pre-adhan notification via WhatsApp"""
        message = f"🕌 Prayer Time Reminder\n\n"
        message += f"Assalamu Alaikum, {user.username}!\n"
        message += f"It's almost time for {prayer_name} prayer.\n"
        message += f"Prayer time: {prayer_time.strftime('%I:%M %p')}\n\n"
        message += "May Allah accept your prayers. 🤲"
        
        return self.send_message(user.whatsapp_number, message)
