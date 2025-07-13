# SalatTracker/trigger_utils.py - NEW FILE for trigger-based prayer fetching

import requests
from datetime import datetime, date
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.contrib.auth import get_user_model
from .models import DailyPrayer, PrayerTime
from users.models import PrayerMethod

User = get_user_model()


def trigger_fetch_prayer_times(user_id, target_date=None):
    """
    Synchronously fetch prayer times for user on target date
    This runs immediately when called - no Celery involved
    """
    try:
        user = User.objects.select_related('prayer_method').get(pk=user_id)
        
        if target_date is None:
            target_date = date.today()
        
        # Convert date to API format
        date_str = target_date.strftime('%d-%m-%Y')
        
        # Get or create prayer method
        try:
            prayer_method = user.prayer_method
        except PrayerMethod.DoesNotExist:
            prayer_method = PrayerMethod.objects.create(
                user=user, sn=1, name='Muslim World League'
            )

        # Call prayer times API
        api_url = "http://api.aladhan.com/v1/timingsByCity"
        params = {
            "date": date_str,
            "city": user.city,
            "country": user.country,
            "method": prayer_method.sn,
        }

        response = requests.get(api_url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json().get("data", {}).get("timings", {})
            date_info = response.json()["data"]["date"]["gregorian"]
            gregorian_date = date_info['date']
            gregorian_weekday = date_info['weekday']['en']

            # Parse and format date
            gregorian_dt = datetime.strptime(gregorian_date, "%d-%m-%Y")
            gregorian_date_formatted = gregorian_dt.strftime("%Y-%m-%d")

            # Create or update daily prayer
            daily_prayer, created = DailyPrayer.objects.get_or_create(
                user=user,
                prayer_date=gregorian_date_formatted,
                defaults={"weekday_name": gregorian_weekday}
            )
            
            if not created:
                daily_prayer.weekday_name = gregorian_weekday
                daily_prayer.save(update_fields=['weekday_name'])

            # Save prayer times
            prayer_times_created = 0
            prayer_times_updated = 0
            
            for prayer_name, prayer_time in data.items():
                prayer_time_obj, pt_created = PrayerTime.objects.get_or_create(
                    daily_prayer=daily_prayer,
                    prayer_name=prayer_name,
                    defaults={"prayer_time": parse_time(prayer_time)}
                )
                
                if pt_created:
                    prayer_times_created += 1
                else:
                    # Update existing prayer time
                    prayer_time_obj.prayer_time = parse_time(prayer_time)
                    prayer_time_obj.save(update_fields=['prayer_time'])
                    prayer_times_updated += 1

            return {
                "status": "success",
                "user_id": user_id,
                "username": user.username,
                "date": target_date.strftime('%Y-%m-%d'),
                "weekday": gregorian_weekday,
                "prayer_count": len(data),
                "daily_prayer_created": created,
                "prayer_times_created": prayer_times_created,
                "prayer_times_updated": prayer_times_updated,
                "daily_prayer_id": daily_prayer.id,
                "fetch_time": timezone.now().isoformat()
            }

        else:
            return {
                "status": "error", 
                "message": "Failed to fetch prayer times from API",
                "status_code": response.status_code,
                "user_id": user_id,
                "date": target_date.strftime('%Y-%m-%d'),
                "api_response": response.text[:200] if response.text else None
            }
            
    except User.DoesNotExist:
        return {
            "status": "error", 
            "reason": "User not found", 
            "user_id": user_id
        }
    except requests.exceptions.Timeout:
        return {
            "status": "error", 
            "reason": "API request timeout", 
            "user_id": user_id,
            "date": target_date.strftime('%Y-%m-%d') if target_date else None
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error", 
            "reason": f"Network error: {str(e)}", 
            "user_id": user_id,
            "date": target_date.strftime('%Y-%m-%d') if target_date else None
        }
    except Exception as e:
        return {
            "status": "error", 
            "reason": f"Unexpected error: {str(e)}", 
            "user_id": user_id,
            "date": target_date.strftime('%Y-%m-%d') if target_date else None
        }


def check_prayer_times_availability(user, target_date=None):
    """
    Check if prayer times are available for user on target date
    Returns availability status without fetching
    """
    if target_date is None:
        target_date = date.today()
    
    try:
        daily_prayer = DailyPrayer.objects.filter(
            user=user, 
            prayer_date=target_date
        ).prefetch_related('prayer_times').first()
        
        if daily_prayer and daily_prayer.prayer_times.exists():
            prayer_count = daily_prayer.prayer_times.count()
            return {
                "available": True,
                "daily_prayer_id": daily_prayer.id,
                "prayer_count": prayer_count,
                "date": target_date.strftime('%Y-%m-%d'),
                "weekday": daily_prayer.weekday_name,
                "needs_fetch": False
            }
        else:
            return {
                "available": False,
                "daily_prayer_id": daily_prayer.id if daily_prayer else None,
                "prayer_count": 0,
                "date": target_date.strftime('%Y-%m-%d'),
                "weekday": daily_prayer.weekday_name if daily_prayer else None,
                "needs_fetch": True
            }
            
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "date": target_date.strftime('%Y-%m-%d'),
            "needs_fetch": True
        }


def get_dashboard_prayer_data(user, target_date=None):
    """
    Get prayer data for dashboard - returns immediately with availability status
    """
    if target_date is None:
        target_date = date.today()
    
    availability = check_prayer_times_availability(user, target_date)
    
    if availability["available"]:
        # Get prayer times
        daily_prayer = DailyPrayer.objects.filter(
            user=user, 
            prayer_date=target_date
        ).prefetch_related('prayer_times').first()
        
        prayer_times = []
        next_prayer = None
        remaining_count = 0
        current_time = timezone.now().time()
        
        for pt in daily_prayer.prayer_times.all().order_by('prayer_time'):
            is_past = pt.prayer_time < current_time if target_date == date.today() else False
            
            prayer_times.append({
                'id': pt.id,
                'name': pt.prayer_name,
                'time': pt.prayer_time.strftime('%H:%M'),
                'time_12h': pt.prayer_time.strftime('%I:%M %p'),
                'is_past': is_past,
                'is_sms_notified': pt.is_sms_notified,
                'is_phonecall_notified': pt.is_phonecall_notified
            })
            
            # Calculate next prayer for today
            if target_date == date.today() and not is_past and next_prayer is None:
                next_prayer = {
                    'name': pt.prayer_name,
                    'time': pt.prayer_time.strftime('%I:%M %p'),
                    'time_24h': pt.prayer_time.strftime('%H:%M'),
                    'minutes_remaining': int((datetime.combine(target_date, pt.prayer_time) - 
                                            datetime.combine(target_date, current_time)).total_seconds() / 60)
                }
            
            if not is_past:
                remaining_count += 1
        
        return {
            "has_prayer_times": True,
            "prayer_times": prayer_times,
            "next_prayer": next_prayer,
            "remaining_prayers": remaining_count,
            "date_info": {
                "date": target_date.strftime('%Y-%m-%d'),
                "weekday": daily_prayer.weekday_name,
                "is_today": target_date == date.today()
            },
            "fetch_needed": False
        }
    else:
        return {
            "has_prayer_times": False,
            "prayer_times": [],
            "next_prayer": None,
            "remaining_prayers": 0,
            "date_info": {
                "date": target_date.strftime('%Y-%m-%d'),
                "weekday": None,
                "is_today": target_date == date.today()
            },
            "fetch_needed": True,
            "fetch_trigger_url": f"/api/trigger-fetch-prayer-times/"
        }