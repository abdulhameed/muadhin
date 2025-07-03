from rest_framework import serializers

from subscriptions.services.subscription_service import SubscriptionService
from .models import UserPreferences, PrayerMethod, PrayerOffset, CustomUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Get the default token data
        data = super().validate(attrs)
        
        # Add user information to the response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'sex': self.user.sex,
            'address': self.user.address,
            'city': self.user.city,
            'country': self.user.country,
            'timezone': self.user.timezone,
            'phone_number': self.user.phone_number,
            'is_active': self.user.is_active,
            'date_joined': self.user.date_joined,
        }
        
        return data
    
    
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'sex', 'address', 'city', 'country', 'timezone', 'phone_number')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=True,  # Set is_active to False
        )

        for field in ['sex', 'address', 'city', 'country', 'timezone', 'phone_number']:
            if field in validated_data:
                setattr(user, field, validated_data[field])
        user.save()
        return user

    # def create(self, validated_data):
    #     user = CustomUser.objects.create_user(**validated_data)
    #     return user


class UserPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for UserPreferences with subscription validation
    """
    # Add read-only fields to show what plan supports
    available_daily_summary_methods = serializers.SerializerMethodField()
    available_pre_adhan_methods = serializers.SerializerMethodField()
    available_adhan_call_methods = serializers.SerializerMethodField()
    current_plan = serializers.SerializerMethodField()

    class Meta:
        model = UserPreferences
        fields = '__all__'
        read_only_fields = ['user']

    def get_available_daily_summary_methods(self, obj):
        """Get available daily summary methods for user's current plan"""
        user = obj.user
        available = []
        for method, _ in UserPreferences.NOTIFICATION_METHODS:
            if SubscriptionService.validate_notification_preference(user, 'daily_prayer_summary', method):
                available.append({'value': method, 'label': dict(UserPreferences.NOTIFICATION_METHODS)[method]})
        return available

    def get_available_pre_adhan_methods(self, obj):
        """Get available pre-adhan methods for user's current plan"""
        user = obj.user
        available = []
        for method, _ in UserPreferences.NOTIFICATION_METHODS:
            if SubscriptionService.validate_notification_preference(user, 'pre_adhan', method):
                available.append({'value': method, 'label': dict(UserPreferences.NOTIFICATION_METHODS)[method]})
        return available

    def get_available_adhan_call_methods(self, obj):
        """Get available adhan call methods for user's current plan"""
        user = obj.user
        available = []
        for method, _ in UserPreferences.ADHAN_METHODS:
            if SubscriptionService.validate_notification_preference(user, 'adhan_call', method):
                available.append({'value': method, 'label': dict(UserPreferences.ADHAN_METHODS)[method]})
        return available

    def get_current_plan(self, obj):
        """Get user's current subscription plan info"""
        user = obj.user
        plan = user.current_plan
        return {
            'name': plan.name,
            'type': plan.plan_type,
            'price': float(plan.price),
            'max_notifications_per_day': plan.max_notifications_per_day,
        }

    def validate_daily_prayer_summary_message_method(self, value):
        """Validate daily prayer summary method against subscription"""
        user = self.context['request'].user if 'request' in self.context else None
        if user and not SubscriptionService.validate_notification_preference(user, 'daily_prayer_summary', value):
            available_methods = []
            for method, _ in UserPreferences.NOTIFICATION_METHODS:
                if SubscriptionService.validate_notification_preference(user, 'daily_prayer_summary', method):
                    available_methods.append(dict(UserPreferences.NOTIFICATION_METHODS)[method])
            
            raise serializers.ValidationError(
                f"Your current plan does not support {dict(UserPreferences.NOTIFICATION_METHODS)[value]} "
                f"for daily summaries. Available methods: {', '.join(available_methods) or 'None (upgrade required)'}"
            )
        return value

    def validate_notification_before_prayer(self, value):
        """Validate pre-adhan notification method against subscription"""
        user = self.context['request'].user if 'request' in self.context else None
        if user and not SubscriptionService.validate_notification_preference(user, 'pre_adhan', value):
            available_methods = []
            for method, _ in UserPreferences.NOTIFICATION_METHODS:
                if SubscriptionService.validate_notification_preference(user, 'pre_adhan', method):
                    available_methods.append(dict(UserPreferences.NOTIFICATION_METHODS)[method])
            
            raise serializers.ValidationError(
                f"Your current plan does not support {dict(UserPreferences.NOTIFICATION_METHODS)[value]} "
                f"for pre-adhan notifications. Available methods: {', '.join(available_methods) or 'None (upgrade required)'}"
            )
        return value

    def validate_adhan_call_method(self, value):
        """Validate adhan call method against subscription"""
        user = self.context['request'].user if 'request' in self.context else None
        if user and not SubscriptionService.validate_notification_preference(user, 'adhan_call', value):
            available_methods = []
            for method, _ in UserPreferences.ADHAN_METHODS:
                if SubscriptionService.validate_notification_preference(user, 'adhan_call', method):
                    available_methods.append(dict(UserPreferences.ADHAN_METHODS)[method])
            
            raise serializers.ValidationError(
                f"Your current plan does not support {dict(UserPreferences.ADHAN_METHODS)[value]} "
                f"for adhan calls. Available methods: {', '.join(available_methods) or 'None (upgrade required)'}"
            )
        return value



# BUG: perform_update and perform_destroy don't belong in serializer
# TODO: These should be in the ViewSet
class PrayerMethodSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = PrayerMethod
        fields = ['id', 'user', 'name', 'sn']
        read_only_fields = ['user']  # User set automatically

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Remove user update logic - user shouldn't change
        instance.sn = validated_data.get('sn', instance.sn)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance

    # def perform_update(self, serializer):
    #     # Get the current authenticated user
    #     user = self.context['request'].user

    #     # Update the instance with the user instance
    #     instance = serializer.save(user=user)

    #     return instance

    # def perform_destroy(self, instance):
    #     # Get the current authenticated user
    #     user = self.context['request'].user

    #     # Check if the user is the owner of the instance
    #     if instance.user != user:
    #         raise serializers.ValidationError("You are not authorized to delete this prayer method.")

    #     # Delete the instance
    #     instance.delete()


class PrayerOffsetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerOffset
        fields = '__all__'
        read_only_fields = ['user']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
