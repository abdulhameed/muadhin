from rest_framework import serializers
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
        # user.sex = validated_data.get('sex', '')
        # user.address = validated_data.get('address', '')
        # user.city = validated_data.get('city', 'ABUJA')
        # user.country = validated_data.get('country', 'NIGERIA')
        # user.timezone = validated_data.get('timezone', 'Africa/Lagos')
        # user.phone_number = validated_data.get('phone_number', '')
        # Set other fields
        for field in ['sex', 'address', 'city', 'country', 'timezone', 'phone_number']:
            if field in validated_data:
                setattr(user, field, validated_data[field])
        user.save()
        return user

    # def create(self, validated_data):
    #     user = CustomUser.objects.create_user(**validated_data)
    #     return user


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = '__all__'


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

    def perform_update(self, serializer):
        # Get the current authenticated user
        user = self.context['request'].user

        # Update the instance with the user instance
        instance = serializer.save(user=user)

        return instance

    def perform_destroy(self, instance):
        # Get the current authenticated user
        user = self.context['request'].user

        # Check if the user is the owner of the instance
        if instance.user != user:
            raise serializers.ValidationError("You are not authorized to delete this prayer method.")

        # Delete the instance
        instance.delete()


class PrayerOffsetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerOffset
        fields = '__all__'
