# SalatTracker/sync_views.py - NEW FILE (completely separate from existing api_views.py)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import DailyPrayer, PrayerTime
from .sync_utils import (
    sync_fetch_prayer_times,
    ensure_prayer_times_exist,
    sync_send_daily_summary,
    get_next_prayer_info,
    get_user_subscription_info
)
from users.models import UserPreferences

User = get_user_model()


class SyncDashboardView(APIView):
    """
    NEW: Dashboard with automatic prayer time fetching (no Celery)
    Completely separate from existing DashboardAPIView
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = date.today()
        
        # Auto-ensure prayer times exist for today
        ensure_result = ensure_prayer_times_exist(user, today)
        
        # Get prayer data
        daily_prayer = DailyPrayer.objects.filter(
            user=user, 
            prayer_date=today
        ).prefetch_related('prayer_times').first()
        
        if not daily_prayer:
            # Fallback to most recent data
            daily_prayer = DailyPrayer.objects.filter(
                user=user
            ).prefetch_related('prayer_times').order_by('-prayer_date').first()
            
            if not daily_prayer:
                return Response({
                    'error': 'No prayer times available',
                    'message': 'Unable to fetch prayer times. Please check your connection and try again.',
                    'fetch_result': ensure_result,
                    'user_info': self._get_user_info(user),
                    'suggestions': [
                        'Check your internet connection',
                        'Verify your location settings',
                        'Try the manual refresh button'
                    ]
                }, status=404)
        
        # Get prayer times
        prayer_times = list(daily_prayer.prayer_times.all().order_by('prayer_time'))
        is_today = daily_prayer.prayer_date == today
        
        # Get user preferences
        user_preferences = self._get_user_preferences(user)
        
        # Build comprehensive response
        response_data = {
            'user_info': self._get_user_info(user),
            'subscription': get_user_subscription_info(user),
            'fetch_info': {
                'auto_fetch_result': ensure_result,
                'data_source': 'today' if is_today else 'fallback',
                'last_updated': daily_prayer.prayer_date.strftime('%Y-%m-%d')
            },
            'date_info': {
                'today': today.strftime('%Y-%m-%d'),
                'showing_date': daily_prayer.prayer_date.strftime('%Y-%m-%d'),
                'weekday': daily_prayer.weekday_name,
                'is_current_day': is_today,
                'hijri_date': None  # Can be added later
            }
        }
        
        if is_today and prayer_times:
            # Calculate next prayer info
            next_prayer_info, remaining_count = get_next_prayer_info(prayer_times)
            response_data.update({
                'next_prayer': next_prayer_info,
                'remaining_prayers_today': remaining_count,
                'current_time': timezone.now().strftime('%H:%M'),
                'timezone': user.timezone
            })
        else:
            response_data.update({
                'next_prayer': self._get_fallback_next_prayer(),
                'remaining_prayers_today': 0,
                'note': 'Showing historical data' if not is_today else 'No prayer times available'
            })
        
        # Add prayer list with notification info
        response_data['prayers'] = self._format_prayers_with_notifications(
            prayer_times, user, user_preferences
        )
        
        # Add quick actions
        response_data['actions'] = {
            'can_refresh': True,
            'can_send_summary': is_today and not daily_prayer.is_email_notified,
            'can_update_preferences': True
        }
        
        return Response(response_data)
    
    def _get_user_info(self, user):
        """Get basic user information"""
        return {
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'username': user.username,
            'email': user.email,
            'location': f"{user.city}, {user.country}",
            'timezone': user.timezone,
            'city': user.city,
            'country': user.country
        }
    
    def _get_user_preferences(self, user):
        """Get user preferences safely"""
        try:
            return user.preferences
        except UserPreferences.DoesNotExist:
            return None
    
    def _get_fallback_next_prayer(self):
        """Return fallback next prayer info"""
        return {
            'prayer_name': 'Not available',
            'prayer_time': 'Please refresh',
            'prayer_time_24h': '00:00',
            'minutes_remaining': 0,
            'time_until': 'Refresh needed'
        }
    
    def _format_prayers_with_notifications(self, prayer_times, user, user_preferences):
        """Format prayer times with notification channel info"""
        prayers = []
        
        for prayer_time in prayer_times:
            prayer_info = {
                'id': prayer_time.id,
                'name': prayer_time.prayer_name,
                'time_12h': prayer_time.prayer_time.strftime('%I:%M %p'),
                'time_24h': prayer_time.prayer_time.strftime('%H:%M'),
                'is_past': prayer_time.prayer_time < timezone.now().time(),
                'notifications': self._get_notification_status(user, user_preferences),
                'status': {
                    'sms_notified': prayer_time.is_sms_notified,
                    'call_notified': prayer_time.is_phonecall_notified
                }
            }
            prayers.append(prayer_info)
        
        return prayers
    
    def _get_notification_status(self, user, user_preferences):
        """Get notification channel status"""
        if not user_preferences:
            return {
                'pre_prayer': {'method': 'email', 'enabled': True, 'timing': '15 min before'},
                'at_prayer': {'method': 'email', 'enabled': True, 'timing': 'At prayer time'},
                'daily_summary': {'method': 'email', 'enabled': True, 'timing': 'Once daily'}
            }
        
        return {
            'pre_prayer': {
                'method': user_preferences.notification_before_prayer,
                'enabled': user_preferences.notification_before_prayer_enabled,
                'timing': f"{user_preferences.notification_time_before_prayer} min before"
            },
            'at_prayer': {
                'method': user_preferences.adhan_call_method,
                'enabled': user_preferences.adhan_call_enabled,
                'timing': 'At prayer time'
            },
            'daily_summary': {
                'method': user_preferences.daily_prayer_summary_message_method,
                'enabled': user_preferences.daily_prayer_summary_enabled,
                'timing': 'Once daily'
            }
        }


class SyncRefreshView(APIView):
    """
    NEW: Manual refresh prayer times (no Celery)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        target_date = request.data.get('date')
        force_refresh = request.data.get('force', False)
        
        # Parse and validate date
        if target_date:
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    "error": "Invalid date format", 
                    "message": "Use YYYY-MM-DD format",
                    "example": "2024-12-25"
                }, status=400)
        else:
            target_date = date.today()
        
        date_str = target_date.strftime('%d-%m-%Y')
        
        # Check if already exists (unless force refresh)
        if not force_refresh:
            existing = DailyPrayer.objects.filter(
                user=user, 
                prayer_date=target_date
            ).exists()
            
            if existing:
                return Response({
                    "message": "Prayer times already exist for this date",
                    "date": target_date.strftime('%Y-%m-%d'),
                    "suggestion": "Use force=true to refresh anyway"
                })
        
        # Fetch prayer times
        result = sync_fetch_prayer_times(user.id, date_str)
        
        if result['status'] == 'success':
            return Response({
                "message": "Prayer times refreshed successfully",
                "date": target_date.strftime('%Y-%m-%d'),
                "result": result,
                "prayer_count": result.get('prayer_count', 0),
                "was_created": result.get('created_new', False)
            })
        else:
            return Response({
                "error": "Failed to refresh prayer times",
                "date": target_date.strftime('%Y-%m-%d'),
                "details": result,
                "suggestions": [
                    "Check your internet connection",
                    "Verify your location settings in profile",
                    "Try again in a few moments"
                ]
            }, status=400)


class SyncSendSummaryView(APIView):
    """
    NEW: Send daily prayer summary email (no Celery)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Check if summary already sent today
        today = date.today()
        daily_prayer = DailyPrayer.objects.filter(
            user=user, 
            prayer_date=today
        ).first()
        
        if not daily_prayer:
            return Response({
                "error": "No prayer times found for today",
                "message": "Please fetch today's prayer times first",
                "suggestion": "Use the refresh button to get prayer times"
            }, status=404)
        
        if daily_prayer.is_email_notified:
            return Response({
                "message": "Daily summary already sent today",
                "date": today.strftime('%Y-%m-%d'),
                "suggestion": "Summary is sent once per day"
            })
        
        # Send summary
        result = sync_send_daily_summary(user.id)
        
        if result['status'] == 'success':
            return Response({
                "message": "Daily prayer summary sent successfully",
                "email": user.email,
                "date": today.strftime('%Y-%m-%d'),
                "prayer_count": result.get('prayer_count', 0)
            })
        else:
            return Response({
                "error": "Failed to send daily summary",
                "details": result,
                "suggestions": [
                    "Check your email settings",
                    "Verify your email address",
                    "Try again in a few moments"
                ]
            }, status=400)


class SyncPrayerTimesView(APIView):
    """
    NEW: Get prayer times for specific date with auto-fetch
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        date_param = request.query_params.get('date')
        
        # Parse date
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    "error": "Invalid date format",
                    "message": "Use YYYY-MM-DD format"
                }, status=400)
        else:
            target_date = date.today()
        
        # Ensure prayer times exist
        ensure_result = ensure_prayer_times_exist(user, target_date)
        
        # Get prayer data
        daily_prayer = DailyPrayer.objects.filter(
            user=user,
            prayer_date=target_date
        ).prefetch_related('prayer_times').first()
        
        if not daily_prayer:
            return Response({
                "error": "No prayer times available",
                "date": target_date.strftime('%Y-%m-%d'),
                "fetch_result": ensure_result
            }, status=404)
        
        # Format prayer times
        prayer_times = []
        for pt in daily_prayer.prayer_times.all().order_by('prayer_time'):
            prayer_times.append({
                'id': pt.id,
                'name': pt.prayer_name,
                'time': pt.prayer_time.strftime('%H:%M'),
                'time_12h': pt.prayer_time.strftime('%I:%M %p'),
                'is_past': pt.prayer_time < timezone.now().time() if target_date == date.today() else False
            })
        
        return Response({
            'date': target_date.strftime('%Y-%m-%d'),
            'weekday': daily_prayer.weekday_name,
            'prayer_times': prayer_times,
            'count': len(prayer_times),
            'fetch_info': ensure_result,
            'is_today': target_date == date.today()
        })


class SyncHealthView(APIView):
    """
    NEW: Health check for sync services
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check various components
        health_info = {
            'sync_service': 'operational',
            'user_info': {
                'id': user.id,
                'username': user.username,
                'location': f"{user.city}, {user.country}"
            },
            'database': 'connected',
            'api_access': 'unknown',
            'last_prayer_data': None
        }
        
        # Check last prayer data
        try:
            latest_prayer = DailyPrayer.objects.filter(user=user).order_by('-prayer_date').first()
            if latest_prayer:
                health_info['last_prayer_data'] = {
                    'date': latest_prayer.prayer_date.strftime('%Y-%m-%d'),
                    'weekday': latest_prayer.weekday_name,
                    'prayer_count': latest_prayer.prayer_times.count()
                }
        except Exception as e:
            health_info['database'] = f'error: {str(e)}'
        
        # Quick API test
        try:
            import requests
            response = requests.get(
                "http://api.aladhan.com/v1/timingsByCity",
                params={
                    "date": date.today().strftime('%d-%m-%Y'),
                    "city": user.city,
                    "country": user.country,
                    "method": 1
                },
                timeout=10
            )
            health_info['api_access'] = 'operational' if response.status_code == 200 else f'error: {response.status_code}'
        except Exception as e:
            health_info['api_access'] = f'error: {str(e)}'
        
        return Response(health_info)