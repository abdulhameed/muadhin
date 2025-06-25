from celery import shared_task
from datetime import date, datetime, timedelta, time
import pytz
from subscriptions.models import NotificationUsage
from subscriptions.services.subscription_service import SubscriptionService
from subscriptions.services.whatsapp_service import WhatsAppService
from users.models import UserPreferences, PrayerMethod
from SalatTracker.models import PrayerTime, DailyPrayer
import requests
from twilio.rest import Client
from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django_mailgun_mime.backends import MailgunMIMEBackend
from django.utils.dateparse import parse_time


TWILIO_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
TWILIO_NUMBER = settings.TWILIO_PHONE_NUMBER
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

User = get_user_model()


@shared_task
def schedule_midnight_checks():
    """
    Celery task that schedules individual tasks to check each user's upcoming midnight.
    """
    for user in User.objects.all():
        user_timezone = pytz.timezone(user.timezone)
        next_midnight = user.next_midnight
        check_user_midnight.apply_async(args=[user.id], eta=next_midnight)

@shared_task
def check_user_midnight(user_id):
    """
    Celery task that checks if a user's midnight is approaching and calls the `fetch_and_save_daily_prayer_times`.
    """
    user = User.objects.get(id=user_id)
    now = datetime.now(pytz.timezone(user.timezone))
    time_to_midnight = user.next_midnight - now
    # Check if the task hasn't been scheduled in the last 24 hours
    last_scheduled = user.last_scheduled_time
    if (
        0 < time_to_midnight.total_seconds() < 600
        and (not last_scheduled or now - last_scheduled > timedelta(hours=24))
    ):  # 600 seconds = 10 minutes
        print(f"Processing---> {user.username}")
        fetch_and_save_daily_prayer_times.delay(user.id, now.date().strftime('%d-%m-%Y'))
        user.last_scheduled_time = now
        user.save()


@shared_task
def fetch_and_save_daily_prayer_times(user_id, date):
    user = User.objects.get(pk=user_id)
    # prayer_method = PrayerMethod.objects.get(user=user)
    try:
        prayer_method = PrayerMethod.objects.get(user=user)
    except PrayerMethod.DoesNotExist:
        # Create default or handle gracefully
        prayer_method = PrayerMethod.objects.create(user=user, sn=1, name='Muslim World League')

    api_url = "http://api.aladhan.com/v1/timingsByCity"
    params = {
        "date": date,
        "city": user.city,
        "country": user.country,
        "method": prayer_method.sn,
    }

    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json().get("data", {}).get("timings", {})
        date_info = response.json()["data"]["date"]["gregorian"]
        gregorian_date = date_info['date']
        gregorian_weekday = date_info['weekday']['en']

        # Parse date
        gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")
        gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

        daily_prayer, created = DailyPrayer.objects.get_or_create(
            user=user,
            prayer_date=gregorian_date_formatted,
            defaults={
                "weekday_name": gregorian_weekday,
            }
        )
        if not created:
            daily_prayer.weekday_name = gregorian_weekday
            daily_prayer.save()

        response_data = {
                "timings": data,
                "gregorian_date": gregorian_date,
                "gregorian_weekday": gregorian_weekday,
            }

        for prayer_name, prayer_time in data.items():
            prayer_time_obj, created = PrayerTime.objects.get_or_create(
                daily_prayer=daily_prayer,
                prayer_name=prayer_name,
                defaults={
                    "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
                }
            )
            if not created:
                prayer_time_obj.prayer_time = parse_time(prayer_time)
                prayer_time_obj.save()
                
        # Call the function to send the daily prayer message
        send_daily_prayer_message.delay(user.id)
        schedule_notifications_for_day.delay(user_id, gregorian_date_formatted)
        schedule_phone_calls_for_day.delay(user_id, gregorian_date_formatted)

        # ✅ Return JSON-serializable data instead of Response
        return {
            "status": "success",
            "timings": data,
            "gregorian_date": gregorian_date,
            "gregorian_weekday": gregorian_weekday,
        }

        # Call the function to send the notification
        # send_daily_prayer_notification(user)
    else:
        # Handle the error case
        # Handle the error case
        # ✅ Return JSON-serializable data instead of Response
        return {
            "status": "error", 
            "message": "Failed to fetch prayer times",
            "status_code": response.status_code
        }


def send_sms(phone_number, message):
    """
    Helper function to send an SMS using Twilio, disabled for costing too much on testing.
    """
    # twilio_client.messages.create(
    #     body=message,
    #     from_=TWILIO_NUMBER,
    #     to=phone_number
    # )
    print(f"<<<<<<<<Fake Texting: {phone_number} From {TWILIO_NUMBER} with TWILIO>>>>>>>>>: ")
    # print(f"SID: {message.sid} Status: {message.status}")
    # print(message.sid)


@shared_task
def send_daily_prayer_message(user_id):
    """Send daily prayer message respecting subscription limits"""
    try:
        user = User.objects.get(id=user_id)
        
        # Check if user can send notifications
        if not user.can_send_notification('daily_summary'):
            return {"status": "skipped", "reason": "Daily limit reached"}
        
        daily_prayer = DailyPrayer.objects.filter(user=user, prayer_date=date.today()).first()
        user_preference = UserPreferences.objects.filter(user=user).first()
        
        if not daily_prayer or not user_preference:
            return {"status": "error", "reason": "Missing data"}
        
        prayer_times = PrayerTime.objects.filter(daily_prayer=daily_prayer)
        method = user_preference.daily_prayer_summary_message_method
        
        # Check if user's plan supports the chosen method
        if not SubscriptionService.validate_notification_preference(user, 'daily_prayer_summary', method):
            # Fall back to email if available
            if user.has_feature('daily_prayer_summary_email'):
                method = 'email'
            else:
                return {"status": "error", "reason": "Feature not available in current plan"}
        
        success = False
        error_message = None
        
        try:
            if method == 'email':
                email_daily_prayerTime(user, daily_prayer, prayer_times)
                daily_prayer.is_email_notified = True
                success = True
            
            elif method == 'whatsapp':
                if user.whatsapp_number:
                    whatsapp_service = WhatsAppService()
                    whatsapp_service.send_daily_prayer_summary(user, prayer_times)
                    success = True
                else:
                    error_message = "WhatsApp number not provided"
            
            elif method == 'sms':
                if user.phone_number:
                    message = f"Assalamu Alaikum, {user.username}!\n\nToday's prayer times:\n"
                    for prayer_time in prayer_times:
                        message += f"{prayer_time.prayer_name}: {prayer_time.prayer_time.strftime('%I:%M %p')}\n"
                    send_sms(user.phone_number, message)
                    daily_prayer.is_sms_notified = True
                    success = True
                else:
                    error_message = "Phone number not provided"
            
            if success:
                daily_prayer.save()
                user.record_notification_sent()
                
                # Log the notification
                NotificationUsage.objects.create(
                    user=user,
                    notification_type=method,
                    success=True
                )
                
                return {"status": "success", "method": method}
            else:
                NotificationUsage.objects.create(
                    user=user,
                    notification_type=method,
                    success=False,
                    error_message=error_message
                )
                return {"status": "error", "reason": error_message}
                
        except Exception as e:
            NotificationUsage.objects.create(
                user=user,
                notification_type=method,
                success=False,
                error_message=str(e)
            )
            return {"status": "error", "reason": str(e)}
            
    except User.DoesNotExist:
        return {"status": "error", "reason": "User not found"}


# @shared_task
# def send_daily_prayer_message(user_id):
#     """
#     Function to send the daily prayer message to the user.
#     """

#     User = get_user_model()  # Get the User model

#     try:
#         user = User.objects.get(id=user_id)  # Retrieve the User instance
#     except User.DoesNotExist:
#         # Handle the case where the user doesn't exist
#         return
    
#     # Get the DailyPrayer object for the current day
#     today = date.today()
#     daily_prayer = DailyPrayer.objects.filter(user=user, prayer_date=today).first()
#     user_preference = UserPreferences.objects.filter(user=user).first()

#     # Check subscription permissions
#     if not user.has_feature('daily_prayer_summary_email') and user_preference.daily_prayer_message_method == 'email':
#         return  # User plan doesn't allow email summaries
    
#     if not user.has_feature('daily_prayer_summary_whatsapp') and user_preference.daily_prayer_message_method == 'whatsapp':
#         return  # User plan doesn't allow WhatsApp summaries

#     if daily_prayer:
#         # Get the prayer times for the current day
#         prayer_times = PrayerTime.objects.filter(daily_prayer=daily_prayer)

#         message = f"Assalamu Alaikum, {user.username}!\n\nToday's prayer times are:\n"
#         for prayer_time in prayer_times:
#             message += f"{prayer_time.prayer_name}: {prayer_time.prayer_time.strftime('%I:%M %p')}\n"

#         if user_preference.daily_prayer_message_method == 'email':
#             # Send the daily prayer email
#             email_daily_prayerTime(user, daily_prayer, prayer_times)
#             # user.email_user('Daily Prayer Times', message)
#             daily_prayer.is_email_notified = True
#             daily_prayer.save()
#         elif user_preference.daily_prayer_message_method == 'sms':
#             send_sms(user.phone_number, message)
#             daily_prayer.is_sms_notified = True  # Change this to is_sms_notified
#             daily_prayer.save()
#         elif user_preference.daily_prayer_message_method == 'whatsapp':    
#             whatsapp_service = WhatsAppService()
#             whatsapp_service.send_message(user.whatsapp_number, message)
#         # Add other notification methods as needed
#     else:
#         # Fetch and save prayer times for the current day if it doesn't exist
#         fetch_and_save_daily_prayer_times.delay(user.id, today.strftime('%d-%m-%Y'))

    


def email_daily_prayerTime(user, daily_prayer, prayer_times):
    """
    Helper function to render and send the daily prayer email.
    """
    # Render the email template with prayer times and date
    context = {
        'user': user,
        'prayer_date': daily_prayer.prayer_date,
        'weekday_name': daily_prayer.weekday_name,
        'prayer_times': prayer_times,
    }
    email_body = render_to_string('SalatTracker/daily_prayer_email.html', context)

    # Send the email
    email_subject = f"Daily Prayer Times for {daily_prayer.prayer_date}"
    email = MailgunMIMEBackend(
        api_key=settings.MAILGUN_API_KEY,
        domain=settings.MAILGUN_DOMAIN_NAME
    )
    email.send_email(
        subject=email_subject,
        body=email_body,
        from_email='your_email@example.com',
        to_emails=[user.email],
        html_message=email_body
    )


def send_pre_prayer_notification_email(email, prayer_name, prayer_time):
    # Render the HTML email template with context
    context = {
        'prayer_name': prayer_name,
        'prayer_time': prayer_time.strftime('%I:%M %p'), # Format the time in 12-hour format
    }
    html_content = render_to_string('SalatTracker/pre_prayer_notification.html', context)
    text_content = strip_tags(html_content) # Plain text version of the email

    # Send the email
    email_subject = f'Prayer Time Notification: {prayer_name}'
    email = MailgunMIMEBackend(
        api_key=settings.MAILGUN_API_KEY,
        domain=settings.MAILGUN_DOMAIN_NAME
    )
    email.send_email(
        subject=email_subject,
        body=text_content,
        from_email='your_email@example.com',
        to_emails=[email],
        html_message=html_content
    )


@shared_task
def schedule_notifications_for_day(user_id, gregorian_date_formatted):
    user = User.objects.get(pk=user_id)
    user_timezone = pytz.timezone(user.timezone)
    current_date = user_timezone.localize(datetime.strptime(gregorian_date_formatted, '%Y-%m-%d')).date()

    user_preferences = UserPreferences.objects.get(user=user)
    daily_prayer = DailyPrayer.objects.get(user=user, prayer_date=current_date)

    # Schedule notifications for each prayer time
    for prayer_time_obj in daily_prayer.prayer_times.all():
        prayer_datetime = datetime.combine(current_date, prayer_time_obj.prayer_time)
        notification_time_delta = timezone.timedelta(minutes=user_preferences.notification_time_before_prayer)
        notification_time = (prayer_datetime - notification_time_delta).time()

        send_pre_adhan_notification.apply_async(
            (user_id, prayer_time_obj.prayer_name, prayer_time_obj.prayer_time),
            eta=datetime.combine(current_date, notification_time)
        )


@shared_task
def send_pre_adhan_notification(user_id, prayer_name, prayer_time):
    """Send pre-adhan notification respecting subscription limits"""
    try:
        user = User.objects.get(pk=user_id)
        
        # Check if user can send notifications
        if not user.can_send_notification('pre_adhan'):
            return {"status": "skipped", "reason": "Daily limit reached"}
        
        user_preferences = UserPreferences.objects.get(user=user)
        method = user_preferences.notification_before_prayer
        
        # Check if user's plan supports the chosen method
        if not SubscriptionService.validate_notification_preference(user, 'pre_adhan', method):
            # Fall back to email if available
            if user.has_feature('pre_adhan_email'):
                method = 'email'
            else:
                return {"status": "error", "reason": "Feature not available in current plan"}
        
        success = False
        error_message = None
        
        try:
            if method == 'email':
                send_pre_prayer_notification_email(user.email, prayer_name, prayer_time)
                success = True
            
            elif method == 'whatsapp':
                if user.whatsapp_number:
                    whatsapp_service = WhatsAppService()
                    whatsapp_service.send_pre_adhan_notification(user, prayer_name, prayer_time)
                    success = True
                else:
                    error_message = "WhatsApp number not provided"
            
            elif method == 'sms':
                if user.phone_number:
                    message = f'Assalamu Alaikum! Prayer time ({prayer_name}) is approaching at {prayer_time.strftime("%I:%M %p")}.'
                    send_sms(user.phone_number, message)
                    success = True
                else:
                    error_message = "Phone number not provided"
            
            if success:
                user.record_notification_sent()
                
                # Log the notification
                NotificationUsage.objects.create(
                    user=user,
                    notification_type=method,
                    prayer_name=prayer_name,
                    success=True
                )
                
                return {"status": "success", "method": method}
            else:
                NotificationUsage.objects.create(
                    user=user,
                    notification_type=method,
                    prayer_name=prayer_name,
                    success=False,
                    error_message=error_message
                )
                return {"status": "error", "reason": error_message}
                
        except Exception as e:
            NotificationUsage.objects.create(
                user=user,
                notification_type=method,
                prayer_name=prayer_name,
                success=False,
                error_message=str(e)
            )
            return {"status": "error", "reason": str(e)}
            
    except (User.DoesNotExist, UserPreferences.DoesNotExist) as e:
        return {"status": "error", "reason": str(e)}




# @shared_task
# def send_pre_adhan_notification(user_id, prayer_name, prayer_time):
#     user = User.objects.get(pk=user_id)
#     email = user.email
#     user_preferences = UserPreferences.objects.get(user=user)
#     notification_method = user_preferences.notification_before_prayer

#     if notification_method == 'sms':
#         send_sms(user.phone_number, f'Prayer time ({prayer_name}) is approaching.')
#     elif notification_method == 'email':
#         # send_email(user.email, f'Prayer time ({prayer_name}) is approaching.')
#         send_pre_prayer_notification_email(email, prayer_name, prayer_time)
#     # Add more notification methods as needed


@shared_task
def schedule_phone_calls_for_day(user_id, date):

    date = datetime.strptime(date, '%Y-%m-%d').date()
    user = User.objects.get(pk=user_id)
    user_preferences = UserPreferences.objects.get(user=user)
    daily_prayer = DailyPrayer.objects.get(user=user, prayer_date=date)

    if user_preferences.adhan_call_method == 'call':
        adhan_audio_url = 'https://media.sd.ma/assabile/adhan_3435370/0bf83c80b583.mp3'
        for prayer_time_obj in daily_prayer.prayer_times.all():
            prayer_time = prayer_time_obj.prayer_time
            call_datetime = datetime.combine(date, prayer_time)
            make_call_and_play_audio.apply_async((user.phone_number, adhan_audio_url), eta=call_datetime)
            

@shared_task
def make_call_and_play_audio(recipient_phone_number, audio_url, user_id):
    """Make adhan call respecting subscription limits"""
    try:
        user = User.objects.get(pk=user_id)
        
        # Check if user's plan supports audio calls
        if not user.has_feature('adhan_call_audio'):
            # Check if text call is available
            if user.has_feature('adhan_call_text'):
                # Send text message instead
                message = "🕌 Adhan - It's time for prayer! Allahu Akbar!"
                send_sms(recipient_phone_number, message)
                return {"status": "success", "method": "text_fallback"}
            else:
                return {"status": "error", "reason": "Adhan calls not available in current plan"}
        
        # Check daily limits
        if not user.can_send_notification('adhan_call'):
            return {"status": "skipped", "reason": "Daily limit reached"}
        
        # Make the actual call
        call = twilio_client.calls.create(
            twiml=f'<Response><Play>{audio_url}</Play></Response>',
            to=recipient_phone_number,
            from_=TWILIO_NUMBER
        )
        
        user.record_notification_sent()
        
        # Log the notification
        NotificationUsage.objects.create(
            user=user,
            notification_type='call',
            success=True
        )
        
        return {"status": "success", "call_sid": call.sid}
        
    except Exception as e:
        if 'user_id' in locals():
            NotificationUsage.objects.create(
                user=User.objects.get(pk=user_id),
                notification_type='call',
                success=False,
                error_message=str(e)
            )
        return {"status": "error", "reason": str(e)}

##################################################

@shared_task 
def notify_prayer_time(prayer_time_id):
  prayer = PrayerTime.objects.get(id=prayer_time_id)
  user = prayer.user.phone_number
  
  # Create Twilio client
  client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
  prayer = PrayerTime.objects.get(id=prayer_time_id)

  # Calculate SMS schedule time
  sms_time = prayer.prayer_time - timedelta(minutes=15)  

  # Send SMS
  message = f"Assalamu Alaikum. In 15 minutes, it will be time for {prayer.prayer_name} prayer. Muadhin will make an adhan call to you at the time."
  
  client.messages.create(
    to=user.phone, 
    from_=TWILIO_NUMBER,
    body=message,
    schedule_time=sms_time 
  )

  # Schedule call
  call_time = prayer.prayer_time 
  client.calls.create(
    to=user.phone,
    from_=TWILIO_NUMBER,
    url="http://your_url.com/prayer_call_recording",
    schedule_time=call_time
  )
