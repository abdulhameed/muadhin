from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from .services.provider_registry import ProviderRegistry
from .services.notification_service import NotificationService
from .models import CommunicationLog, ProviderStatus

User = get_user_model()


class ProviderStatusAPIView(APIView):
    """API endpoint to check provider status and performance"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get provider status for user's country"""
        user = request.user
        country_code = getattr(user, 'country', 'US')[:2].upper()
        
        # Get providers for user's country
        providers = ProviderRegistry.get_providers_for_country(country_code)
        
        provider_info = []
        for provider in providers:
            # Get status from database
            try:
                status = ProviderStatus.objects.get(
                    provider_name=provider.name,
                    country_code=country_code
                )
            except ProviderStatus.DoesNotExist:
                status = None
            
            provider_info.append({
                'name': provider.name,
                'configured': provider.is_configured,
                'cost_per_message': provider.get_cost_per_message(country_code),
                'health': {
                    'is_healthy': status.is_healthy if status else True,
                    'success_rate': status.success_rate if status else 100.0,
                    'total_attempts': status.total_attempts if status else 0,
                    'average_response_time': status.average_response_time_ms if status else 0,
                } if status else None
            })
        
        return Response({
            'user_country': country_code,
            'available_providers': len(providers),
            'providers': provider_info,
            'recommendation': self._get_recommendation(provider_info)
        })


class AdminProviderAnalyticsAPIView(APIView):
    """Admin-only endpoint for provider analytics and cost analysis"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get comprehensive provider analytics"""
        # Date range for analysis
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get communication logs for the period
        logs = CommunicationLog.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        # Overall statistics
        total_communications = logs.count()
        successful_communications = logs.filter(success=True).count()
        total_cost = logs.aggregate(total=Sum('cost'))['total'] or 0
        
        # Provider breakdown
        provider_stats = logs.values('provider_name').annotate(
            count=Count('id'),
            success_count=Count('id', filter=models.Q(success=True)),
            total_cost=Sum('cost'),
            avg_cost=Avg('cost')
        ).order_by('-count')
        
        # Country breakdown
        country_stats = logs.values('country_code').annotate(
            count=Count('id'),
            total_cost=Sum('cost'),
            unique_providers=Count('provider_name', distinct=True)
        ).order_by('-count')
        
        # Communication type breakdown
        type_stats = logs.values('communication_type').annotate(
            count=Count('id'),
            success_count=Count('id', filter=models.Q(success=True)),
            total_cost=Sum('cost')
        ).order_by('-count')
        
        # Cost comparison (estimate savings vs all-Twilio)
        twilio_cost_estimate = self._calculate_twilio_only_cost(logs)
        actual_cost = total_cost
        estimated_savings = twilio_cost_estimate - actual_cost
        
        return Response({
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': end_date.date()
            },
            'overview': {
                'total_communications': total_communications,
                'successful_communications': successful_communications,
                'success_rate': (successful_communications / max(total_communications, 1)) * 100,
                'total_cost': float(total_cost),
                'average_cost': float(total_cost / max(total_communications, 1))
            },
            'cost_analysis': {
                'actual_cost': float(actual_cost),
                'estimated_twilio_only_cost': float(twilio_cost_estimate),
                'estimated_savings': float(estimated_savings),
                'savings_percentage': (estimated_savings / max(twilio_cost_estimate, 1)) * 100
            },
            'breakdown': {
                'by_provider': list(provider_stats),
                'by_country': list(country_stats),
                'by_type': list(type_stats)
            },
            'top_countries': self._get_top_countries_with_savings(),
        })
    
    def _calculate_twilio_only_cost(self, logs):
        """Calculate what the cost would be if using only Twilio"""
        twilio_cost = 0
        twilio_provider = ProviderRegistry.get_provider('twilio')
        
        if not twilio_provider:
            return 0
        
        for log in logs:
            country = log.country_code or 'US'
            cost = twilio_provider.get_cost_per_message(country)
            twilio_cost += cost
        
        return twilio_cost
    
    def _get_top_countries_with_savings(self):
        """Get top countries where we're saving the most money"""
        # This would involve comparing actual costs vs Twilio costs by country
        # Simplified version here
        country_logs = CommunicationLog.objects.values('country_code').annotate(
            count=Count('id'),
            total_cost=Sum('cost')
        ).order_by('-count')[:10]
        
        savings_by_country = []
        twilio_provider = ProviderRegistry.get_provider('twilio')
        
        for country_data in country_logs:
            country = country_data['country_code'] or 'US'
            actual_cost = country_data['total_cost'] or 0
            
            if twilio_provider:
                twilio_unit_cost = twilio_provider.get_cost_per_message(country)
                estimated_twilio_cost = twilio_unit_cost * country_data['count']
                savings = estimated_twilio_cost - actual_cost
            else:
                savings = 0
                estimated_twilio_cost = 0
            
            savings_by_country.append({
                'country': country,
                'message_count': country_data['count'],
                'actual_cost': float(actual_cost),
                'estimated_twilio_cost': float(estimated_twilio_cost),
                'savings': float(savings),
                'savings_percentage': (savings / max(estimated_twilio_cost, 1)) * 100
            })
        
        return sorted(savings_by_country, key=lambda x: x['savings'], reverse=True)
    
    def _get_recommendation(self, provider_info):
        """Get recommendation for user based on provider status"""
        healthy_providers = [p for p in provider_info if p.get('health', {}).get('is_healthy', True)]
        
        if not healthy_providers:
            return "⚠️ No healthy providers available. Check system status."
        
        cheapest = min(healthy_providers, key=lambda x: x['cost_per_message'])
        
        return f"💡 Recommended: {cheapest['name']} (${cheapest['cost_per_message']:.4f} per message)"


class TestNotificationAPIView(APIView):
    """API endpoint for testing notifications"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send test notification"""
        user = request.user
        notification_type = request.data.get('type', 'sms')  # sms, call, whatsapp
        test_message = request.data.get('message', '🧪 Test notification from Muadhin')
        
        # Check if user has required contact info
        if notification_type == 'sms' and not user.phone_number:
            return Response({
                'error': 'Phone number required for SMS test',
                'required_field': 'phone_number'
            }, status=400)
        
        if notification_type == 'whatsapp' and not getattr(user, 'whatsapp_number', None):
            return Response({
                'error': 'WhatsApp number required for WhatsApp test',
                'required_field': 'whatsapp_number'
            }, status=400)
        
        try:
            if notification_type == 'sms':
                result = NotificationService.send_sms(user, test_message, log_usage=False)
            elif notification_type == 'call':
                result = NotificationService.make_text_call(user, test_message, log_usage=False)
            elif notification_type == 'whatsapp':
                result = NotificationService.send_whatsapp(user, test_message, log_usage=False)
            else:
                return Response({'error': 'Invalid notification type'}, status=400)
            
            if result.success:
                return Response({
                    'success': True,
                    'message': f'Test {notification_type} sent successfully',
                    'provider': result.provider_name,
                    'message_id': result.message_id,
                    'cost': result.cost
                })
            else:
                return Response({
                    'success': False,
                    'error': result.error_message,
                    'provider_attempted': result.provider_name
                }, status=400)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
