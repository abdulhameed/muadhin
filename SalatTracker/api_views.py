from rest_framework import viewsets

from SalatTracker.tasks import fetch_and_save_daily_prayer_times
from subscriptions.services.subscription_service import SubscriptionService
from .models import PrayerTime
from .serializers import PrayerTimeSerializer, DailyPrayerSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime, date, timedelta
import requests
from users.models import CustomUser, PrayerMethod, UserPreferences
from .models import PrayerTime, DailyPrayer
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated


class DailyPrayerViewSet(viewsets.ModelViewSet):
    queryset = DailyPrayer.objects.all()
    serializer_class = DailyPrayerSerializer

    @action(detail=False, methods=['GET'])
    def get_daily_prayer_for_user_and_day(self, request, user_id, prayer_date):
        try:
            daily_prayer = DailyPrayer.objects.get(user=user_id, prayer_date=prayer_date)
            serializer = DailyPrayerSerializer(daily_prayer)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response("Daily prayer not found for the given user and date", status=404)


class PrayerTimeViewSet(viewsets.ModelViewSet):
    queryset = PrayerTime.objects.all()
    serializer_class = PrayerTimeSerializer

    @action(detail=False, methods=['GET'])
    def get_prayer_times_for_user_and_day(self, request, user_id, prayer_date):
        try:
            daily_prayer = DailyPrayer.objects.get(user=user_id, prayer_date=prayer_date)
            # FIXED: Use correct related_name
            prayer_times = daily_prayer.prayer_times.all()
            serializer = PrayerTimeSerializer(prayer_times, many=True)
            return Response(serializer.data)
        except DailyPrayer.DoesNotExist:
            return Response({"error": "Prayer times not found for the given user and date"}, status=404)


class PrayerTimeFetch(APIView):
    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(pk=user_id)
            # FIXED: Handle missing PrayerMethod
            prayer_method, created = PrayerMethod.objects.get_or_create(
                user=user,
                defaults={'sn': 1, 'name': 'Muslim World League'}
            )
            date = request.query_params.get('date', datetime.now().strftime('%d-%m-%Y'))
            fetch_and_save_daily_prayer_times.delay(user_id, date)
            return Response({"message": "Prayer times are being fetched and saved."})
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class DashboardAPIView(APIView):
    """
    API endpoint that returns dashboard information:
    1. Next prayer details
    2. Current subscription plan
    3. Remaining prayers today
    4. All prayer times with enabled notification channels
    
    Falls back to most recent prayer times if today's aren't available.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = date.today()
        
        # First try to get today's prayers
        daily_prayer = None
        prayer_times = None
        is_today = True
        
        try:
            daily_prayer = DailyPrayer.objects.get(user=user, prayer_date=today)
            prayer_times = daily_prayer.prayer_times.all().order_by('prayer_time')
        except DailyPrayer.DoesNotExist:
            # Fallback to most recent prayer data
            daily_prayer = DailyPrayer.objects.filter(
                user=user
            ).order_by('-prayer_date').first()
            
            if daily_prayer:
                prayer_times = daily_prayer.prayer_times.all().order_by('prayer_time')
                is_today = False
            else:
                # No prayer data found at all
                return Response({
                    'error': 'No prayer times found',
                    'message': 'No prayer times have been generated yet. Please fetch prayer times first.',
                    'user': {
                        'name': user.get_full_name() or user.username,
                        'location': f"{user.city}, {user.country}",
                        'timezone': user.timezone
                    }
                }, status=404)
        
        # Get user preferences
        try:
            user_preferences = UserPreferences.objects.get(user=user)
        except UserPreferences.DoesNotExist:
            user_preferences = None
        
        # Get subscription info
        current_plan = SubscriptionService.get_user_plan(user)
        
        # Get subscription details
        subscription_info = self._get_subscription_info(user, current_plan)
        
        # Find next prayer and count remaining (only relevant if using today's data)
        if is_today:
            next_prayer_info, remaining_count = self._get_next_prayer_info(prayer_times)
        else:
            # For fallback data, we can't determine "next" prayer or remaining count
            next_prayer_info = {
                'prayer_name': 'Unknown',
                'prayer_time': 'Please fetch today\'s prayer times',
                'prayer_time_24h': '00:00',
                'minutes_remaining': 0,
                'time_until': 'Update required'
            }
            remaining_count = 0
        
        # Get all prayers with notification channels
        prayers_with_notifications = self._get_prayers_with_notifications(
            prayer_times, user, user_preferences
        )
        
        # Prepare date information
        date_info = {
            'date_shown': daily_prayer.prayer_date.strftime('%Y-%m-%d'),
            'weekday': daily_prayer.weekday_name,
            'is_today': is_today,
            'hijri_date': None  # You can add Hijri date if needed
        }
        
        # Add fallback message if not today's data
        if not is_today:
            date_info['fallback_message'] = f'Showing prayer times from {daily_prayer.prayer_date.strftime("%B %d, %Y")} (most recent available)'
            date_info['today'] = today.strftime('%Y-%m-%d')
        else:
            date_info['today'] = today.strftime('%Y-%m-%d')
        
        return Response({
            'user': {
                'name': user.get_full_name() or user.username,
                'location': f"{user.city}, {user.country}",
                'timezone': user.timezone
            },
            'next_prayer': next_prayer_info,
            'subscription': subscription_info,
            'remaining_prayers_today': remaining_count,
            'todays_prayers': prayers_with_notifications,
            'date': date_info
        })
    
    def _get_subscription_info(self, user, current_plan):
        """Get subscription information"""
        try:
            subscription = user.subscription
            return {
                'plan_name': current_plan.name,
                'plan_type': current_plan.plan_type,
                'price': float(current_plan.price),
                'status': subscription.status,
                'is_trial': subscription.is_trial,
                'days_remaining': subscription.days_remaining,
                'end_date': subscription.end_date.strftime('%b %d, %Y') if subscription.end_date else None,
                'notifications_sent_today': subscription.notifications_sent_today,
                'max_notifications_per_day': current_plan.max_notifications_per_day,
                'features': current_plan.features_list
            }
        except:
            # User has no subscription (basic plan)
            return {
                'plan_name': current_plan.name,
                'plan_type': current_plan.plan_type,
                'price': float(current_plan.price),
                'status': 'basic',
                'is_trial': False,
                'days_remaining': None,
                'end_date': None,
                'notifications_sent_today': 0,
                'max_notifications_per_day': current_plan.max_notifications_per_day,
                'features': current_plan.features_list
            }
    
    def _get_next_prayer_info(self, prayer_times):
        """Find the next prayer and count remaining prayers"""
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
            
            # Convert to minutes
            minutes_remaining = int(time_diff.total_seconds() / 60)
            
            return {
                'prayer_name': next_prayer.prayer_name,
                'prayer_time': next_prayer.prayer_time.strftime('%I:%M %p'),
                'prayer_time_24h': next_prayer.prayer_time.strftime('%H:%M'),
                'minutes_remaining': minutes_remaining,
                'time_until': self._format_time_remaining(minutes_remaining)
            }, remaining_count
        else:
            # All prayers for today have passed
            return {
                'prayer_name': 'Fajr',
                'prayer_time': 'Tomorrow',
                'prayer_time_24h': '00:00',
                'minutes_remaining': 0,
                'time_until': 'Next day'
            }, 0
    
    def _format_time_remaining(self, minutes):
        """Format time remaining in a user-friendly way"""
        if minutes < 60:
            return f"{minutes} minutes"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours} hour{'s' if hours != 1 else ''}"
            else:
                return f"{hours}h {remaining_minutes}m"
    
    def _get_prayers_with_notifications(self, prayer_times, user, user_preferences):
        """Get all prayers with their enabled notification channels"""
        prayers = []
        
        for prayer_time in prayer_times:
            # Get enabled notification channels for this prayer
            enabled_channels = self._get_enabled_channels(user, user_preferences)
            
            prayers.append({
                'prayer_name': prayer_time.prayer_name,
                'prayer_time': prayer_time.prayer_time.strftime('%I:%M %p'),
                'prayer_time_24h': prayer_time.prayer_time.strftime('%H:%M'),
                'notification_channels': enabled_channels,
                'is_notified': {
                    'sms': prayer_time.is_sms_notified,
                    'phone_call': prayer_time.is_phonecall_notified
                }
            })
        
        return prayers
    
    def _get_enabled_channels(self, user, user_preferences):
        """Get enabled notification channels based on user preferences and subscription"""
        if not user_preferences:
            return {
                'pre_adhan': None,
                'adhan_call': None,
                'daily_summary': 'email'  # Default
            }
        
        # Check what user has configured vs what their plan allows
        enabled_channels = {}
        
        # Pre-adhan notifications
        pre_adhan_method = user_preferences.notification_before_prayer
        if SubscriptionService.validate_notification_preference(user, 'pre_adhan', pre_adhan_method):
            enabled_channels['pre_adhan'] = {
                'method': pre_adhan_method,
                'timing': f"{user_preferences.notification_time_before_prayer} minutes before",
                'icon': self._get_method_icon(pre_adhan_method),
                'enabled': True
            }
        else:
            enabled_channels['pre_adhan'] = {
                'method': pre_adhan_method,
                'timing': f"{user_preferences.notification_time_before_prayer} minutes before",
                'icon': self._get_method_icon(pre_adhan_method),
                'enabled': False,
                'reason': 'Upgrade required'
            }
        
        # Adhan call
        adhan_method = user_preferences.adhan_call_method
        if SubscriptionService.validate_notification_preference(user, 'adhan_call', adhan_method):
            enabled_channels['adhan_call'] = {
                'method': adhan_method,
                'timing': 'At prayer time',
                'icon': self._get_method_icon(adhan_method),
                'enabled': True
            }
        else:
            enabled_channels['adhan_call'] = {
                'method': adhan_method,
                'timing': 'At prayer time',
                'icon': self._get_method_icon(adhan_method),
                'enabled': False,
                'reason': 'Upgrade required'
            }
        
        # Daily summary (only relevant for morning)
        summary_method = user_preferences.daily_prayer_summary_message_method
        if SubscriptionService.validate_notification_preference(user, 'daily_prayer_summary', summary_method):
            enabled_channels['daily_summary'] = {
                'method': summary_method,
                'timing': 'Once per day',
                'icon': self._get_method_icon(summary_method),
                'enabled': True
            }
        else:
            enabled_channels['daily_summary'] = {
                'method': summary_method,
                'timing': 'Once per day',
                'icon': self._get_method_icon(summary_method),
                'enabled': False,
                'reason': 'Upgrade required'
            }
        
        return enabled_channels
    
    def _get_method_icon(self, method):
        """Get icon/emoji for notification method"""
        icons = {
            'email': '📧',
            'sms': '📱',
            'whatsapp': '💬',
            'call': '📞',
            'text': '📝',
            'off': '🚫'
        }
        return icons.get(method, '❓')
# This code defines a Django REST Framework API view for fetching and displaying prayer times, user subscription details, and notification preferences.
# git add . && git commit -m "Add DashboardAPIView for user prayer times and subscription details" && git push
# class DashboardAPIView(APIView):
#     """
#     API endpoint that returns dashboard information:
#     1. Next prayer details
#     2. Current subscription plan
#     3. Remaining prayers today
#     4. All prayer times with enabled notification channels
#     """
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         user = request.user
#         today = date.today()
        
#         try:
#             # Get today's prayers
#             daily_prayer = DailyPrayer.objects.get(user=user, prayer_date=today)
#             prayer_times = daily_prayer.prayer_times.all().order_by('prayer_time')
            
#             # Get user preferences
#             try:
#                 user_preferences = UserPreferences.objects.get(user=user)
#             except UserPreferences.DoesNotExist:
#                 user_preferences = None
            
#             # Get subscription info
#             current_plan = SubscriptionService.get_user_plan(user)
            
#             # Get subscription details
#             subscription_info = self._get_subscription_info(user, current_plan)
            
#             # Find next prayer and count remaining
#             next_prayer_info, remaining_count = self._get_next_prayer_info(prayer_times)
            
#             # Get all prayers with notification channels
#             prayers_with_notifications = self._get_prayers_with_notifications(
#                 prayer_times, user, user_preferences
#             )
            
#             return Response({
#                 'user': {
#                     'name': user.get_full_name() or user.username,
#                     'location': f"{user.city}, {user.country}",
#                     'timezone': user.timezone
#                 },
#                 'next_prayer': next_prayer_info,
#                 'subscription': subscription_info,
#                 'remaining_prayers_today': remaining_count,
#                 'todays_prayers': prayers_with_notifications,
#                 'date': {
#                     'today': today.strftime('%Y-%m-%d'),
#                     'weekday': daily_prayer.weekday_name,
#                     'hijri_date': None  # You can add Hijri date if needed
#                 }
#             })
            
#         except DailyPrayer.DoesNotExist:
#             return Response({
#                 'error': 'No prayer times found for today',
#                 'message': 'Prayer times have not been generated for today yet.'
#             }, status=404)
    
#     def _get_subscription_info(self, user, current_plan):
#         """Get subscription information"""
#         try:
#             subscription = user.subscription
#             return {
#                 'plan_name': current_plan.name,
#                 'plan_type': current_plan.plan_type,
#                 'price': float(current_plan.price),
#                 'status': subscription.status,
#                 'is_trial': subscription.is_trial,
#                 'days_remaining': subscription.days_remaining,
#                 'end_date': subscription.end_date.strftime('%b %d, %Y') if subscription.end_date else None,
#                 'notifications_sent_today': subscription.notifications_sent_today,
#                 'max_notifications_per_day': current_plan.max_notifications_per_day,
#                 'features': current_plan.features_list
#             }
#         except:
#             # User has no subscription (basic plan)
#             return {
#                 'plan_name': current_plan.name,
#                 'plan_type': current_plan.plan_type,
#                 'price': float(current_plan.price),
#                 'status': 'basic',
#                 'is_trial': False,
#                 'days_remaining': None,
#                 'end_date': None,
#                 'notifications_sent_today': 0,
#                 'max_notifications_per_day': current_plan.max_notifications_per_day,
#                 'features': current_plan.features_list
#             }
    
#     def _get_next_prayer_info(self, prayer_times):
#         """Find the next prayer and count remaining prayers"""
#         now = timezone.now()
#         current_time = now.time()
        
#         next_prayer = None
#         remaining_count = 0
        
#         for prayer_time in prayer_times:
#             if prayer_time.prayer_time > current_time:
#                 if next_prayer is None:
#                     next_prayer = prayer_time
#                 remaining_count += 1
        
#         if next_prayer:
#             # Calculate time until next prayer
#             next_prayer_datetime = datetime.combine(date.today(), next_prayer.prayer_time)
#             now_datetime = datetime.combine(date.today(), current_time)
#             time_diff = next_prayer_datetime - now_datetime
            
#             # Convert to minutes
#             minutes_remaining = int(time_diff.total_seconds() / 60)
            
#             return {
#                 'prayer_name': next_prayer.prayer_name,
#                 'prayer_time': next_prayer.prayer_time.strftime('%I:%M %p'),
#                 'prayer_time_24h': next_prayer.prayer_time.strftime('%H:%M'),
#                 'minutes_remaining': minutes_remaining,
#                 'time_until': self._format_time_remaining(minutes_remaining)
#             }, remaining_count
#         else:
#             # All prayers for today have passed
#             return {
#                 'prayer_name': 'Fajr',
#                 'prayer_time': 'Tomorrow',
#                 'prayer_time_24h': '00:00',
#                 'minutes_remaining': 0,
#                 'time_until': 'Next day'
#             }, 0
    
#     def _format_time_remaining(self, minutes):
#         """Format time remaining in a user-friendly way"""
#         if minutes < 60:
#             return f"{minutes} minutes"
#         else:
#             hours = minutes // 60
#             remaining_minutes = minutes % 60
#             if remaining_minutes == 0:
#                 return f"{hours} hour{'s' if hours != 1 else ''}"
#             else:
#                 return f"{hours}h {remaining_minutes}m"
    
#     def _get_prayers_with_notifications(self, prayer_times, user, user_preferences):
#         """Get all prayers with their enabled notification channels"""
#         prayers = []
        
#         for prayer_time in prayer_times:
#             # Get enabled notification channels for this prayer
#             enabled_channels = self._get_enabled_channels(user, user_preferences)
            
#             prayers.append({
#                 'prayer_name': prayer_time.prayer_name,
#                 'prayer_time': prayer_time.prayer_time.strftime('%I:%M %p'),
#                 'prayer_time_24h': prayer_time.prayer_time.strftime('%H:%M'),
#                 'notification_channels': enabled_channels,
#                 'is_notified': {
#                     'sms': prayer_time.is_sms_notified,
#                     'phone_call': prayer_time.is_phonecall_notified
#                 }
#             })
        
#         return prayers
    
#     def _get_enabled_channels(self, user, user_preferences):
#         """Get enabled notification channels based on user preferences and subscription"""
#         if not user_preferences:
#             return {
#                 'pre_adhan': None,
#                 'adhan_call': None,
#                 'daily_summary': 'email'  # Default
#             }
        
#         # Check what user has configured vs what their plan allows
#         enabled_channels = {}
        
#         # Pre-adhan notifications
#         pre_adhan_method = user_preferences.notification_before_prayer
#         if SubscriptionService.validate_notification_preference(user, 'pre_adhan', pre_adhan_method):
#             enabled_channels['pre_adhan'] = {
#                 'method': pre_adhan_method,
#                 'timing': f"{user_preferences.notification_time_before_prayer} minutes before",
#                 'icon': self._get_method_icon(pre_adhan_method),
#                 'enabled': True
#             }
#         else:
#             enabled_channels['pre_adhan'] = {
#                 'method': pre_adhan_method,
#                 'timing': f"{user_preferences.notification_time_before_prayer} minutes before",
#                 'icon': self._get_method_icon(pre_adhan_method),
#                 'enabled': False,
#                 'reason': 'Upgrade required'
#             }
        
#         # Adhan call
#         adhan_method = user_preferences.adhan_call_method
#         if SubscriptionService.validate_notification_preference(user, 'adhan_call', adhan_method):
#             enabled_channels['adhan_call'] = {
#                 'method': adhan_method,
#                 'timing': 'At prayer time',
#                 'icon': self._get_method_icon(adhan_method),
#                 'enabled': True
#             }
#         else:
#             enabled_channels['adhan_call'] = {
#                 'method': adhan_method,
#                 'timing': 'At prayer time',
#                 'icon': self._get_method_icon(adhan_method),
#                 'enabled': False,
#                 'reason': 'Upgrade required'
#             }
        
#         # Daily summary (only relevant for morning)
#         summary_method = user_preferences.daily_prayer_summary_message_method
#         if SubscriptionService.validate_notification_preference(user, 'daily_prayer_summary', summary_method):
#             enabled_channels['daily_summary'] = {
#                 'method': summary_method,
#                 'timing': 'Once per day',
#                 'icon': self._get_method_icon(summary_method),
#                 'enabled': True
#             }
#         else:
#             enabled_channels['daily_summary'] = {
#                 'method': summary_method,
#                 'timing': 'Once per day',
#                 'icon': self._get_method_icon(summary_method),
#                 'enabled': False,
#                 'reason': 'Upgrade required'
#             }
        
#         return enabled_channels
    
#     def _get_method_icon(self, method):
#         """Get icon/emoji for notification method"""
#         icons = {
#             'email': '📧',
#             'sms': '📱',
#             'whatsapp': '💬',
#             'call': '📞',
#             'text': '📝',
#             'off': '🚫'
#         }
#         return icons.get(method, '❓')
