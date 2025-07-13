# SalatTracker/trigger_views.py - NEW FILE for dashboard + trigger endpoints

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, date
from django.utils import timezone
from django.contrib.auth import get_user_model

from .trigger_utils import (
    trigger_fetch_prayer_times,
    get_dashboard_prayer_data,
    check_prayer_times_availability
)
from subscriptions.services.subscription_service import SubscriptionService

User = get_user_model()


class FastDashboardView(APIView):
    """
    Fast dashboard that returns immediately - doesn't wait for prayer time fetching
    Signals frontend if prayer times need to be fetched via separate trigger endpoint
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        target_date = self._get_target_date(request)
        
        # Get user info
        user_info = {
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'username': user.username,
            'email': user.email,
            'location': f"{user.city}, {user.country}",
            'timezone': user.timezone,
            'city': user.city,
            'country': user.country
        }
        
        # Get subscription info
        subscription_info = self._get_subscription_info(user)
        
        # Get prayer data (returns immediately)
        prayer_data = get_dashboard_prayer_data(user, target_date)
        
        # Get user preferences
        preferences_info = self._get_preferences_info(user)
        
        # Build response
        response = {
            'user': user_info,
            'subscription': subscription_info,
            'preferences': preferences_info,
            'prayer_data': prayer_data,
            'timestamp': timezone.now().isoformat(),
            'response_time': 'immediate'
        }
        
        # Add trigger info if fetch is needed
        if prayer_data.get('fetch_needed'):
            response['action_required'] = {
                'fetch_needed': True,
                'trigger_endpoint': '/api/trigger-fetch-prayer-times/',
                'method': 'POST',
                'payload': {
                    'date': target_date.strftime('%Y-%m-%d')
                },
                'message': 'Prayer times not available. Call trigger endpoint to fetch.'
            }
        else:
            response['action_required'] = {
                'fetch_needed': False,
                'message': 'All data available'
            }
        
        return Response(response)
    
    def _get_target_date(self, request):
        """Get target date from request or default to today"""
        date_param = request.query_params.get('date')
        if date_param:
            try:
                return datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                pass
        return date.today()
    
    def _get_subscription_info(self, user):
        """Get subscription information"""
        try:
            current_plan = SubscriptionService.get_user_plan(user)
            subscription = getattr(user, 'subscription', None)
            
            if subscription:
                return {
                    'plan_name': current_plan.name,
                    'plan_type': current_plan.plan_type,
                    'price': float(current_plan.price),
                    'status': subscription.status,
                    'is_trial': getattr(subscription, 'is_trial', False),
                    'days_remaining': getattr(subscription, 'days_remaining', None),
                    'notifications_sent_today': getattr(subscription, 'notifications_sent_today', 0),
                    'max_notifications_per_day': current_plan.max_notifications_per_day
                }
            else:
                return {
                    'plan_name': current_plan.name,
                    'plan_type': current_plan.plan_type,
                    'price': float(current_plan.price),
                    'status': 'basic',
                    'is_trial': False,
                    'days_remaining': None,
                    'notifications_sent_today': 0,
                    'max_notifications_per_day': current_plan.max_notifications_per_day
                }
        except Exception:
            return {
                'plan_name': 'Basic Plan',
                'plan_type': 'basic',
                'price': 0.0,
                'status': 'basic',
                'error': 'Could not load subscription info'
            }
    
    def _get_preferences_info(self, user):
        """Get user preferences"""
        try:
            prefs = user.preferences
            return {
                'daily_summary_enabled': prefs.daily_prayer_summary_enabled,
                'daily_summary_method': prefs.daily_prayer_summary_message_method,
                'pre_prayer_enabled': prefs.notification_before_prayer_enabled,
                'pre_prayer_method': prefs.notification_before_prayer,
                'pre_prayer_timing': prefs.notification_time_before_prayer,
                'adhan_call_enabled': prefs.adhan_call_enabled,
                'adhan_call_method': prefs.adhan_call_method
            }
        except Exception:
            return {
                'daily_summary_enabled': True,
                'daily_summary_method': 'email',
                'pre_prayer_enabled': True,
                'pre_prayer_method': 'email',
                'pre_prayer_timing': 15,
                'adhan_call_enabled': True,
                'adhan_call_method': 'email',
                'error': 'Could not load preferences'
            }


class TriggerFetchPrayerTimesView(APIView):
    """
    Trigger endpoint that fetches prayer times synchronously
    Called by frontend when dashboard indicates fetch is needed
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Get target date from request
        date_param = request.data.get('date')
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid date format',
                    'message': 'Use YYYY-MM-DD format',
                    'example': '2024-12-25'
                }, status=400)
        else:
            target_date = date.today()
        
        # Check if already exists (unless force is specified)
        force = request.data.get('force', False)
        if not force:
            availability = check_prayer_times_availability(user, target_date)
            if availability['available']:
                return Response({
                    'message': 'Prayer times already exist',
                    'date': target_date.strftime('%Y-%m-%d'),
                    'prayer_count': availability['prayer_count'],
                    'suggestion': 'Use force=true to refetch anyway',
                    'already_available': True
                })
        
        # Trigger the fetch (this runs synchronously)
        start_time = timezone.now()
        result = trigger_fetch_prayer_times(user.id, target_date)
        end_time = timezone.now()
        
        # Calculate execution time
        execution_time = (end_time - start_time).total_seconds()
        
        if result['status'] == 'success':
            return Response({
                'message': 'Prayer times fetched successfully',
                'result': result,
                'execution_time_seconds': execution_time,
                'timestamp': end_time.isoformat(),
                'next_steps': {
                    'refresh_dashboard': True,
                    'dashboard_endpoint': '/api/fast-dashboard/',
                    'message': 'You can now refresh the dashboard to see updated prayer times'
                }
            })
        else:
            return Response({
                'error': 'Failed to fetch prayer times',
                'result': result,
                'execution_time_seconds': execution_time,
                'timestamp': end_time.isoformat(),
                'suggestions': [
                    'Check your internet connection',
                    'Verify your location settings',
                    'Try again in a few moments'
                ]
            }, status=400)


class CheckPrayerAvailabilityView(APIView):
    """
    Quick check endpoint to see if prayer times are available for a date
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get date parameter
        date_param = request.query_params.get('date')
        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid date format',
                    'message': 'Use YYYY-MM-DD format'
                }, status=400)
        else:
            target_date = date.today()
        
        # Check availability
        availability = check_prayer_times_availability(user, target_date)
        
        return Response({
            'date': target_date.strftime('%Y-%m-%d'),
            'availability': availability,
            'actions': {
                'fetch_url': '/api/trigger-fetch-prayer-times/' if availability['needs_fetch'] else None,
                'dashboard_url': '/api/fast-dashboard/',
                'recommended_action': 'fetch_prayer_times' if availability['needs_fetch'] else 'view_dashboard'
            }
        })


class PrayerTimesStatusView(APIView):
    """
    Get status of prayer times for multiple dates
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        dates = request.data.get('dates', [])
        
        if not dates:
            # Default to today and next 7 days
            today = date.today()
            dates = [(today + timezone.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(8)]
        
        results = {}
        
        for date_str in dates:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                availability = check_prayer_times_availability(user, target_date)
                results[date_str] = availability
            except ValueError:
                results[date_str] = {
                    'error': 'Invalid date format',
                    'available': False,
                    'needs_fetch': False
                }
        
        return Response({
            'user_id': user.id,
            'checked_dates': len(results),
            'results': results,
            'summary': {
                'available_count': sum(1 for r in results.values() if r.get('available', False)),
                'needs_fetch_count': sum(1 for r in results.values() if r.get('needs_fetch', False))
            }
        })