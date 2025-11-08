# SalatTracker/sync_utils.py - NEW FILE (completely separate from existing utils.py)

import requests
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import DailyPrayer, PrayerTime
from users.models import PrayerMethod, UserPreferences

User = get_user_model()


def sync_fetch_prayer_times(user_id, date_str):
    """
    NEW: Synchronous prayer time fetching without Celery
    Completely separate from existing fetch_and_save_prayer_times function
    """
    try:
        user = User.objects.select_related('prayer_method').get(pk=user_id)
        
        # Get or create prayer method
        try:
            prayer_method = user.prayer_method
        except PrayerMethod.DoesNotExist:
            prayer_method = PrayerMethod.objects.create(
                user=user, sn=1, name='Muslim World League'
            )

        api_url = "http://api.aladhan.com/v1/timingsByCity"
        params = {
            "date": date_str,
            "city": user.city,
            "country": user.country,
            "method": prayer_method.sn,
        }

        # Fetch from API with timeout
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
            for prayer_name, prayer_time in data.items():
                prayer_time_obj, created = PrayerTime.objects.get_or_create(
                    daily_prayer=daily_prayer,
                    prayer_name=prayer_name,
                    defaults={"prayer_time": parse_time(prayer_time)}
                )
                if not created:
                    prayer_time_obj.prayer_time = parse_time(prayer_time)
                    prayer_time_obj.save(update_fields=['prayer_time'])
                
                if created:
                    prayer_times_created += 1

            return {
                "status": "success",
                "user_id": user_id,
                "username": user.username,
                "date": gregorian_date_formatted,
                "weekday": gregorian_weekday,
                "prayer_count": len(data),
                "created_new": created,
                "prayer_times_created": prayer_times_created,
                "daily_prayer_id": daily_prayer.id,
                "api_date": gregorian_date
            }

        else:
            return {
                "status": "error", 
                "message": "Failed to fetch prayer times from API",
                "status_code": response.status_code,
                "user_id": user_id,
                "api_url": api_url
            }
            
    except User.DoesNotExist:
        return {"status": "error", "reason": "User not found", "user_id": user_id}
    except requests.exceptions.Timeout:
        return {"status": "error", "reason": "API request timeout", "user_id": user_id}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "reason": f"Network error: {str(e)}", "user_id": user_id}
    except Exception as e:
        return {"status": "error", "reason": f"Unexpected error: {str(e)}", "user_id": user_id}


def ensure_prayer_times_exist(user, target_date=None):
    """
    NEW: Ensure prayer times exist for user on target date
    Auto-fetch if missing, return existing if present
    """
    if target_date is None:
        target_date = date.today()
    
    # Check if prayer times already exist
    daily_prayer = DailyPrayer.objects.filter(
        user=user, 
        prayer_date=target_date
    ).prefetch_related('prayer_times').first()
    
    if daily_prayer and daily_prayer.prayer_times.exists():
        return {
            "status": "exists", 
            "daily_prayer_id": daily_prayer.id,
            "date": target_date.strftime('%Y-%m-%d'),
            "prayer_count": daily_prayer.prayer_times.count(),
            "message": "Prayer times already exist"
        }
    
    # Prayer times don't exist, fetch them
    date_str = target_date.strftime('%d-%m-%Y')
    result = sync_fetch_prayer_times(user.id, date_str)
    
    if result['status'] == 'success':
        result['auto_fetched'] = True
        result['message'] = "Prayer times auto-fetched successfully"
    
    return result


def sync_send_daily_summary(user_id):
    """
    NEW: Send daily prayer summary synchronously (email only for now)
    Completely separate from existing send_daily_prayer_message task
    """
    try:
        user = User.objects.select_related('preferences').get(id=user_id)
        today = date.today()
        
        daily_prayer = DailyPrayer.objects.filter(
            user=user, 
            prayer_date=today
        ).prefetch_related('prayer_times').first()
        
        if not daily_prayer:
            return {"status": "error", "reason": "No daily prayer data found for today"}
        
        prayer_times = list(daily_prayer.prayer_times.all())
        
        if not prayer_times:
            return {"status": "error", "reason": "No prayer times found"}
        
        # Get user preferences
        try:
            user_preferences = user.preferences
            method = user_preferences.daily_prayer_summary_message_method
        except UserPreferences.DoesNotExist:
            method = 'email'  # Default to email
        
        # For now, only support email in sync mode
        if method != 'email':
            return {
                "status": "skipped", 
                "reason": f"Method '{method}' not supported in sync mode. Only email is available."
            }
        
        # Send email
        try:
            sync_send_prayer_email(user, daily_prayer, prayer_times)
            
            # Mark as notified
            daily_prayer.is_email_notified = True
            daily_prayer.save(update_fields=['is_email_notified'])
            
            return {
                "status": "success", 
                "method": "email",
                "recipient": user.email,
                "prayer_count": len(prayer_times)
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "reason": f"Failed to send email: {str(e)}"
            }
            
    except User.DoesNotExist:
        return {"status": "error", "reason": "User not found", "user_id": user_id}
    except Exception as e:
        return {"status": "error", "reason": f"Unexpected error: {str(e)}", "user_id": user_id}


def sync_send_prayer_email(user, daily_prayer, prayer_times):
    """
    NEW: Send prayer email synchronously
    """
    try:
        # Render email template
        context = {
            'user': user,
            'prayer_date': daily_prayer.prayer_date,
            'weekday_name': daily_prayer.weekday_name,
            'prayer_times': prayer_times,
        }
        
        html_content = render_to_string(
            'SalatTracker/daily_prayer_email.html', 
            context
        )
        text_content = strip_tags(html_content)

        # Send email
        email_subject = f"Daily Prayer Times for {daily_prayer.prayer_date}"
        
        email = EmailMultiAlternatives(
            subject=email_subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print(f"✅ NEW SYNC: Sent daily prayer email to {user.email}")
        
    except Exception as e:
        print(f"❌ NEW SYNC: Error sending email to {user.email}: {str(e)}")
        raise


def get_next_prayer_info(prayer_times):
    """
    NEW: Calculate next prayer and remaining prayers for today
    """
    if not prayer_times:
        return None, 0
    
    now = timezone.now()
    current_time = now.time()
    
    next_prayer = None
    remaining_count = 0
    
    for prayer_time in prayer_times:
        if prayer_time.prayer_time > current_time:
            if next_prayer is None:
                next_prayer = prayer_time
            remaining_count += 1
    
    if next_prayer:
        # Calculate time until next prayer
        next_prayer_datetime = datetime.combine(date.today(), next_prayer.prayer_time)
        now_datetime = datetime.combine(date.today(), current_time)
        time_diff = next_prayer_datetime - now_datetime
        
        minutes_remaining = int(time_diff.total_seconds() / 60)
        
        return {
            'prayer_name': next_prayer.prayer_name,
            'prayer_time': next_prayer.prayer_time.strftime('%I:%M %p'),
            'prayer_time_24h': next_prayer.prayer_time.strftime('%H:%M'),
            'minutes_remaining': max(0, minutes_remaining),
            'time_until': format_time_remaining(minutes_remaining)
        }, remaining_count
    else:
        # All prayers passed
        return {
            'prayer_name': 'All prayers completed',
            'prayer_time': 'Tomorrow',
            'prayer_time_24h': '00:00',
            'minutes_remaining': 0,
            'time_until': 'Next day'
        }, 0


def format_time_remaining(minutes):
    """
    NEW: Format time remaining in user-friendly way
    """
    if minutes <= 0:
        return "Now"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            return f"{hours}h {remaining_minutes}m"


def get_user_subscription_info(user):
    """
    NEW: Get subscription info without dependencies on other modules
    """
    try:
        # Try to get subscription info
        subscription = getattr(user, 'subscription', None)
        if subscription:
            plan = subscription.plan
            return {
                'plan_name': plan.name,
                'plan_type': plan.plan_type,
                'price': float(plan.price) if plan.price else 0.0,
                'status': subscription.status,
                'is_trial': getattr(subscription, 'is_trial', False),
                'max_notifications': getattr(plan, 'max_notifications_per_day', 15)
            }
    except Exception:
        pass
    
    # Default/fallback subscription info
    return {
        'plan_name': 'Basic Plan',
        'plan_type': 'basic',
        'price': 0.0,
        'status': 'active',
        'is_trial': False,
        'max_notifications': 15
    }