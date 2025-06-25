from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer, SubscriptionHistorySerializer
from .services.subscription_service import SubscriptionService


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing subscription plans"""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.AllowAny]


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
