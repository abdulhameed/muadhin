from celery import Celery, shared_task
from celery.schedules import crontab
# from .models import User  # Import your user profile model
from SalatTracker.models import DailyPrayer, PrayerTime
from SalatTracker.tasks import fetch_and_save_daily_prayer_times, schedule_notifications_for_day, schedule_phone_calls_for_day, send_daily_prayer_message
from django.contrib.auth import get_user_model
import pytz
from datetime import datetime, timedelta
from django.core.cache import cache
from rest_framework.response import Response
import requests
from django.utils import timezone
from django.utils.dateparse import parse_time

from users.models import PrayerMethod
from django.db import models, transaction

User = get_user_model()

app = Celery('users')


@shared_task
def check_and_schedule_daily_tasks():
    """
    Optimized version that processes users in chunks to avoid memory issues
    """
    now = timezone.now()
    
    # Use database filtering instead of loading all users
    # Only get users that might need scheduling (haven't been scheduled recently)
    cutoff_time = now - timedelta(hours=23)  # Users not scheduled in last 23 hours
    
    # Use values_list to only get the data we need, not full objects
    user_ids_to_process = User.objects.filter(
        models.Q(last_scheduled_time__isnull=True) | 
        models.Q(last_scheduled_time__lt=cutoff_time)
    ).values_list('id', flat=True)
    
    # Process users in small chunks to avoid memory issues
    chunk_size = 5  # Process 5 users at a time
    
    for i in range(0, len(user_ids_to_process), chunk_size):
        chunk_ids = user_ids_to_process[i:i + chunk_size]
        process_user_chunk.delay(list(chunk_ids), now.isoformat())


@shared_task
def process_user_chunk(user_ids, now_iso):
    """
    Process a small chunk of users to avoid memory issues
    """
    now = datetime.fromisoformat(now_iso.replace('Z', '+00:00'))
    
    # Only select the fields we need and use iterator for memory efficiency
    users = User.objects.filter(
        id__in=user_ids
    ).select_related('preferences').only(
        'id', 'username', 'timezone', 'last_scheduled_time', 'midnight_utc'
    ).iterator(chunk_size=10)
    
    processed_count = 0
    
    for user in users:
        try:
            # Check if user needs scheduling
            if should_schedule_user(user, now):
                next_date = now.date() + timedelta(days=1)
                
                # Schedule the prayer times fetch
                fetch_and_save_daily_prayer_times.delay(user.id, next_date.strftime('%d-%m-%Y'))
                
                # Update last scheduled time efficiently
                User.objects.filter(id=user.id).update(last_scheduled_time=now)
                processed_count += 1
                
        except Exception as e:
            print(f"❌ Error processing user {user.id}: {str(e)}")
            continue
    
    return {"processed": processed_count, "chunk_size": len(user_ids)}

def should_schedule_user(user, now):
    """
    Determine if a user needs scheduling based on their timezone and last scheduled time
    """
    try:
        if not user.timezone:
            return False
            
        user_timezone = pytz.timezone(user.timezone)
        user_now = now.astimezone(user_timezone)
        
        # Calculate next midnight in user's timezone
        next_midnight = user_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        next_midnight_utc = next_midnight.astimezone(pytz.utc)
        
        # Check if we're within 1 hour of their next midnight
        time_to_midnight = (next_midnight_utc - now).total_seconds()
        
        # Only schedule if:
        # 1. We're within 1 hour of their midnight (3600 seconds)
        # 2. They haven't been scheduled in the last 23 hours
        if 0 < time_to_midnight < 3600:
            last_scheduled = user.last_scheduled_time
            if not last_scheduled or (now - last_scheduled) > timedelta(hours=23):
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error checking schedule for user {user.id}: {str(e)}")
        return False


@shared_task
def fetch_and_save_daily_prayer_times(user_id, date):
    """
    Optimized version with better error handling and memory management
    """
    try:
        # Only get the user fields we need
        user = User.objects.select_related('prayer_method').only(
            'id', 'username', 'city', 'country'
        ).get(pk=user_id)
        
        # Get or create prayer method efficiently
        try:
            prayer_method = user.prayer_method
        except PrayerMethod.DoesNotExist:
            prayer_method = PrayerMethod.objects.create(
                user=user, sn=1, name='Muslim World League'
            )

        api_url = "http://api.aladhan.com/v1/timingsByCity"
        params = {
            "date": date,
            "city": user.city,
            "country": user.country,
            "method": prayer_method.sn,
        }

        # Use timeout to prevent hanging requests
        response = requests.get(api_url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json().get("data", {}).get("timings", {})
            date_info = response.json()["data"]["date"]["gregorian"]
            gregorian_date = date_info['date']
            gregorian_weekday = date_info['weekday']['en']

            # Parse date
            gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")
            gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

            # Use database transaction for consistency
            with transaction.atomic():
                daily_prayer, created = DailyPrayer.objects.get_or_create(
                    user=user,
                    prayer_date=gregorian_date_formatted,
                    defaults={"weekday_name": gregorian_weekday}
                )
                
                if not created:
                    daily_prayer.weekday_name = gregorian_weekday
                    daily_prayer.save(update_fields=['weekday_name'])

                # Bulk create prayer times for efficiency
                prayer_times_to_create = []
                prayer_times_to_update = []
                
                for prayer_name, prayer_time in data.items():
                    try:
                        prayer_time_obj, created = PrayerTime.objects.get_or_create(
                            daily_prayer=daily_prayer,
                            prayer_name=prayer_name,
                            defaults={"prayer_time": parse_time(prayer_time)}
                        )
                        if not created:
                            prayer_time_obj.prayer_time = parse_time(prayer_time)
                            prayer_times_to_update.append(prayer_time_obj)
                    except Exception as e:
                        print(f"❌ Error creating prayer time {prayer_name}: {str(e)}")
                        continue
                
                # Bulk update if needed
                if prayer_times_to_update:
                    PrayerTime.objects.bulk_update(prayer_times_to_update, ['prayer_time'])
                    
            # Schedule related tasks asynchronously to avoid blocking
            send_daily_prayer_message.apply_async(args=[user.id], countdown=5)
            schedule_notifications_for_day.apply_async(
                args=[user_id, gregorian_date_formatted], countdown=10
            )
            schedule_phone_calls_for_day.apply_async(
                args=[user_id, gregorian_date_formatted], countdown=15
            )

            return {
                "status": "success",
                "user_id": user_id,
                "date": gregorian_date_formatted,
                "prayer_count": len(data)
            }

        else:
            return {
                "status": "error", 
                "message": "Failed to fetch prayer times",
                "status_code": response.status_code,
                "user_id": user_id
            }
            
    except User.DoesNotExist:
        return {"status": "error", "reason": "User not found", "user_id": user_id}
    except requests.exceptions.Timeout:
        return {"status": "error", "reason": "API timeout", "user_id": user_id}
    except Exception as e:
        print(f"❌ Error in fetch_and_save_daily_prayer_times for user {user_id}: {str(e)}")
        return {"status": "error", "reason": str(e), "user_id": user_id}

# @shared_task
# def fetch_and_save_daily_prayer_times(user_id, date):
#     user = User.objects.get(pk=user_id)
#     # prayer_method = PrayerMethod.objects.get(user=user)
#     try:
#         prayer_method = PrayerMethod.objects.get(user=user)
#     except PrayerMethod.DoesNotExist:
#         # Create default or handle gracefully
#         prayer_method = PrayerMethod.objects.create(user=user, sn=1, name='Muslim World League')

#     api_url = "http://api.aladhan.com/v1/timingsByCity"
#     params = {
#         "date": date,
#         "city": user.city,
#         "country": user.country,
#         "method": prayer_method.sn,
#     }

#     response = requests.get(api_url, params=params)
#     if response.status_code == 200:
#         data = response.json().get("data", {}).get("timings", {})
#         date_info = response.json()["data"]["date"]["gregorian"]
#         gregorian_date = date_info['date']
#         gregorian_weekday = date_info['weekday']['en']

#         # Parse date
#         gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")
#         gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

#         daily_prayer, created = DailyPrayer.objects.get_or_create(
#             user=user,
#             prayer_date=gregorian_date_formatted,
#             defaults={
#                 "weekday_name": gregorian_weekday,
#             }
#         )
#         if not created:
#             daily_prayer.weekday_name = gregorian_weekday
#             daily_prayer.save()

#         response_data = {
#                 "timings": data,
#                 "gregorian_date": gregorian_date,
#                 "gregorian_weekday": gregorian_weekday,
#             }

#         for prayer_name, prayer_time in data.items():
#             prayer_time_obj, created = PrayerTime.objects.get_or_create(
#                 daily_prayer=daily_prayer,
#                 prayer_name=prayer_name,
#                 defaults={
#                     "prayer_time": timezone.make_aware(datetime.strptime(prayer_time, '%H:%M')),
#                 }
#             )
#             if not created:
#                 prayer_time_obj.prayer_time = parse_time(prayer_time)
#                 # prayer_time_obj.prayer_time = datetime.strptime(prayer_time, '%H:%M')
#                 prayer_time_obj.save()
                
#         # Call the function to send the daily prayer message
#         send_daily_prayer_message.delay(user.id)
#         schedule_notifications_for_day.delay(user_id, gregorian_date_formatted)
#         schedule_phone_calls_for_day.delay(user_id, gregorian_date_formatted)

#         # ✅ Return JSON-serializable data instead of Response
#         return {
#             "status": "success",
#             "timings": data,
#             "gregorian_date": gregorian_date,
#             "gregorian_weekday": gregorian_weekday,
#         }
#         # Call the function to send the notification
#         # send_daily_prayer_notification(user)
#     else:
#         # Handle the error case
#         # ✅ Return JSON-serializable data instead of Response
#         return {
#             "status": "error", 
#             "message": "Failed to fetch prayer times",
#             "status_code": response.status_code
#         }
