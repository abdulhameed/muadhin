from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    features_list = serializers.ReadOnlyField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'price', 'billing_cycle', 
            'description', 'features_list', 'sort_order'
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    days_remaining = serializers.ReadOnlyField()
    is_trial = serializers.ReadOnlyField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'status', 'start_date', 'end_date', 
            'trial_end_date', 'days_remaining', 'is_trial',
            'notifications_sent_today', 'created_at'
        ]


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    from_plan = SubscriptionPlanSerializer(read_only=True)
    to_plan = SubscriptionPlanSerializer(read_only=True)
    
    class Meta:
        model = SubscriptionHistory
        fields = ['id', 'from_plan', 'to_plan', 'change_date', 'reason', 'amount_paid']
