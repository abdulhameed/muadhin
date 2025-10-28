from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer, SubscriptionHistorySerializer
from .services.subscription_service import SubscriptionService
from communications.services.provider_registry import ProviderRegistry


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing subscription plans"""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Filter plans by country if specified"""
        queryset = super().get_queryset()
        country = self.request.query_params.get('country')
        
        if country:
            # Get country-specific plans first, then global fallbacks
            return SubscriptionPlan.get_plans_for_country(country)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with country-specific data"""
        country = request.query_params.get('country')
        response = super().list(request, *args, **kwargs)
        
        if country:
            # Add country-specific metadata
            user_country_info = self._get_country_info(country)
            response.data = {
                'country_info': user_country_info,
                'plans': response.data
            }
            
            # Add localized pricing and savings info to each plan
            for plan_data in response.data['plans']:
                plan = SubscriptionPlan.objects.get(id=plan_data['id'])
                plan_data['localized_price'] = plan.localized_price_display
                
                # Calculate savings vs global plan
                if plan.country != 'GLOBAL':
                    global_plan = SubscriptionPlan.get_best_plan_for_country(plan.plan_type, 'GLOBAL')
                    if global_plan and plan.currency != global_plan.currency:
                        # Rough savings calculation (should use real exchange rates)
                        if plan.currency == 'NGN' and global_plan.currency == 'USD':
                            # Rough conversion for demo (₦1500 vs $9.99)
                            savings = 80 if plan.plan_type == 'basic' else 75
                            plan_data['savings_vs_global'] = f"{savings}%"
        
        return response
    
    def _get_country_info(self, country_code):
        """Get country-specific information"""
        country_mapping = {
            'NG': {
                'name': 'Nigeria',
                'currency': 'NGN',
                'currency_symbol': '₦',
                'flag': '🇳🇬',
                'primary_provider': 'AfricasTalking',
                'cost_advantage': '66% cheaper than global rates'
            },
            'GB': {
                'name': 'United Kingdom', 
                'currency': 'GBP',
                'currency_symbol': '£',
                'flag': '🇬🇧',
                'primary_provider': 'Twilio',
                'cost_advantage': 'Premium global rates'
            }
        }
        
        return country_mapping.get(country_code.upper(), {
            'name': 'Global',
            'currency': 'USD', 
            'currency_symbol': '$',
            'flag': '🌍'
        })
    
    @action(detail=False, methods=['get'])
    def price_comparison(self, request):
        """Compare pricing across countries"""
        country = request.query_params.get('country', 'NG')
        plan_type = request.query_params.get('plan_type', 'basic')
        
        # Get country-specific plan
        country_plan = SubscriptionPlan.get_best_plan_for_country(plan_type, country)
        global_plan = SubscriptionPlan.get_best_plan_for_country(plan_type, 'GLOBAL')
        
        comparison = {
            'country_plan': {
                'name': country_plan.name if country_plan else None,
                'price': country_plan.localized_price_display if country_plan else None,
                'currency': country_plan.currency if country_plan else None,
            },
            'global_plan': {
                'name': global_plan.name if global_plan else None,
                'price': global_plan.localized_price_display if global_plan else None,
                'currency': global_plan.currency if global_plan else None,
            }
        }
        
        # Calculate savings (simplified)
        if country == 'NG' and country_plan and global_plan:
            comparison['savings_percent'] = 80 if plan_type == 'basic' else 75
            comparison['message'] = f"Save {comparison['savings_percent']}% with Nigeria pricing!"
        
        return Response(comparison)
    
    @action(detail=False, methods=['get']) 
    def cost_estimate(self, request):
        """Get SMS cost estimates for country"""
        country = request.query_params.get('country', 'NG')
        message_count = int(request.query_params.get('messages', '30'))  # Monthly estimate
        
        # Get provider cost estimates
        estimates = ProviderRegistry.get_cost_estimate_for_country(country, message_count)
        
        # Get best provider
        best_provider = ProviderRegistry.get_best_provider_for_cost(country)
        
        return Response({
            'country': country,
            'message_count': message_count,
            'provider_estimates': estimates,
            'recommended_provider': {
                'name': best_provider.name if best_provider else None,
                'cost_per_message': best_provider.get_cost_per_message(country) if best_provider else None
            },
            'monthly_cost_estimate': estimates.get(best_provider.name, {}).get('total_cost') if best_provider else None
        })


class UserSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing user subscriptions"""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current user's subscription"""
        try:
            subscription = request.user.subscription
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            # Return basic plan info
            basic_plan = SubscriptionPlan.objects.get(plan_type='basic')
            return Response({
                'plan': SubscriptionPlanSerializer(basic_plan).data,
                'status': 'basic',
                'message': 'Using free basic plan'
            })
    
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """Subscribe to a new plan"""
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return Response(
                {'error': 'plan_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid plan'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Handle subscription logic
        subscription = SubscriptionService.upgrade_user_plan(request.user, plan)
        serializer = self.get_serializer(subscription)
        
        return Response({
            'message': f'Successfully subscribed to {plan.name}',
            'subscription': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def start_trial(self, request):
        """Start a trial subscription"""
        plan_type = request.data.get('plan_type', 'premium')
        trial_days = request.data.get('trial_days', 7)
        
        try:
            subscription = SubscriptionService.start_trial(
                request.user, plan_type, trial_days
            )
            serializer = self.get_serializer(subscription)
            
            return Response({
                'message': f'Trial started successfully for {trial_days} days',
                'subscription': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancel current subscription"""
        try:
            subscription = request.user.subscription
            subscription.cancel_subscription()
            
            return Response({
                'message': 'Subscription cancelled successfully'
            })
        except UserSubscription.DoesNotExist:
            return Response(
                {'error': 'No active subscription found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get subscription history"""
        history = SubscriptionHistory.objects.filter(user=request.user)
        serializer = SubscriptionHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def features(self, request):
        """Get current plan features and usage"""
        plan = SubscriptionService.get_user_plan(request.user)
        
        try:
            subscription = request.user.subscription
            usage_data = {
                'notifications_sent_today': subscription.notifications_sent_today,
                'max_notifications_per_day': plan.max_notifications_per_day,
                'remaining_notifications': max(0, plan.max_notifications_per_day - subscription.notifications_sent_today)
            }
        except UserSubscription.DoesNotExist:
            usage_data = {
                'notifications_sent_today': 0,
                'max_notifications_per_day': plan.max_notifications_per_day,
                'remaining_notifications': plan.max_notifications_per_day
            }
        
        return Response({
            'plan': SubscriptionPlanSerializer(plan).data,
            'usage': usage_data
        })
