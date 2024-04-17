from celery import shared_task
from datetime import datetime, timedelta
import pytz
from users.models import UserPreferences
from SalatTracker.models import PrayerTime
import requests
from twilio.rest import Client
from django.conf import settings


@shared_task
def fetch_and_store_prayer_times():
    # Get the list of users whose current time is equal to utc_time_for_1159
    current_time = datetime.now()

    users = UserPreferences.objects.filter(
        utc_time_for_1159=current_time.strftime('%H:%M:%S')
    )

    for user in users:
        # Fetch prayer times data from an API (replace 'api_url' with the actual API URL)
        api_url = 'https://example.com/api/prayer_times'
        response = requests.get(api_url, params={'location': user.location})

        if response.status_code == 200:
            prayer_times_data = response.json()

            # Extract prayer times from the API response and store them
            for prayer_name, prayer_time in prayer_times_data.items():
                PrayerTime.objects.create(
                    user=user.user,
                    prayer_name=prayer_name,
                    prayer_time=prayer_time,
                    prayer_date=current_time.date(),
                )


TWILIO_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
TWILIO_NUMBER = settings.TWILIO_PHONE_NUMBER
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
