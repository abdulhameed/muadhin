from celery import shared_task
from datetime import date, datetime, timedelta
import pytz
from users.models import UserPreferences, CustomUser, PrayerMethod
from SalatTracker.models import PrayerTime, DailyPrayer
import requests
from twilio.rest import Client
from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


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
    Celery task that checks if a user's midnight is approaching and sends the daily prayer message.
    """
    user = User.objects.get(id=user_id)
    now = datetime.now(pytz.timezone(user.timezone))
    time_to_midnight = user.next_midnight - now
    if 0 < time_to_midnight.total_seconds() < 600:  # 600 seconds = 10 minutes
        fetch_and_save_prayer_times.delay(user.id, now.date().strftime('%d-%m-%Y'))


@shared_task
def fetch_and_save_prayer_times(user_id, date):
    user = CustomUser.objects.get(pk=user_id)
    prayer_method = PrayerMethod.objects.get(user=user)

    api_url = "http://api.aladhan.com/v1/timingsByCity"
    params = {
        "date": date,
        "city": user.city,
        "country": user.country,
        "method": prayer_method.id,
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
                prayer_time_obj.prayer_time = datetime.strptime(prayer_time, '%H:%M')
                prayer_time_obj.save()
                
        # Call the function to send the daily prayer message
        send_daily_prayer_message(user)

        return Response(response_data)

        # Call the function to send the notification
        # send_daily_prayer_notification(user)
    else:
        # Handle the error case
        return Response("Failed to fetch prayer times", status=400)


def send_sms(phone_number, message):
    """
    Helper function to send an SMS using Twilio
    """
    twilio_client.messages.create(
        body=message,
        from_='YOUR_TWILIO_PHONE_NUMBER',
        to=phone_number
    )


def send_daily_prayer_message(user):
    """
    Function to send the daily prayer message to the user.
    """
    # Get the DailyPrayer object for the current day
    today = date.today()
    daily_prayer = DailyPrayer.objects.filter(user=user, prayer_date=today).first()
    user_preference = UserPreferences.objects.filter(user=user).first()

    if daily_prayer:
        # Get the prayer times for the current day
        prayer_times = PrayerTime.objects.filter(daily_prayer=daily_prayer)

        message = f"Assalamu Alaikum, {user.username}!\n\nToday's prayer times are:\n"
        for prayer_time in prayer_times:
            message += f"{prayer_time.prayer_name}: {prayer_time.prayer_time.strftime('%I:%M %p')}\n"

        if user_preference.daily_prayer_message_method == 'email':
            # Send the daily prayer email
            email_daily_prayerTime(user, daily_prayer, prayer_times)
            # user.email_user('Daily Prayer Times', message)
            daily_prayer.is_email_notified = True
            daily_prayer.save()
        elif user_preference.daily_prayer_message_method == 'sms':
            send_sms(user.phone_number, message)
            daily_prayer.is_email_notified = True  # Change this to is_sms_notified
            daily_prayer.save()
        # Add other notification methods as needed
    else:
        # Fetch and save prayer times for the current day if it doesn't exist
        fetch_and_save_prayer_times.delay(user.id, today.strftime('%d-%m-%Y'))


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
    email = EmailMessage(
        subject=email_subject,
        body=email_body,
        from_email='your_email@example.com',
        to=[user.email],
    )
    email.content_subtype = 'html'
    email.send()


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
