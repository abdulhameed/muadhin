from rest_framework import serializers
from .models import UserPreferences, PrayerMethod, PrayerOffset, CustomUser
from django.contrib.auth import get_user_model

User = get_user_model()


# class CustomUserSerializer(serializers.ModelSerializer):

#     password = serializers.CharField(read_only=True)
#     # is_superuser = serializers.BooleanField(read_only=True)
#     class Meta:
#         model = CustomUser
#         exclude = ('is_superuser', 'is_staff', 'is_active', 
#                    'last_login', 'date_joined', 'groups', 'user_permissions')

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'sex', 'address', 'city', 'country', 'timezone', 'phone_number')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        User = get_user_model()
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False,  # Set is_active to False
        )
        user.sex = validated_data.get('sex', '')
        user.address = validated_data.get('address', '')
        user.city = validated_data.get('city', 'ABUJA')
        user.country = validated_data.get('country', 'NIGERIA')
        user.timezone = validated_data.get('timezone', 'Africa/Lagos')
        user.phone_number = validated_data.get('phone_number', '')
        user.save()
        return user

    # def create(self, validated_data):
    #     user = CustomUser.objects.create_user(**validated_data)
    #     return user


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = '__all__'


class PrayerMethodSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    class Meta:
        model = PrayerMethod
        fields = ['id', 'user', 'name', 'sn']

    def create(self, validated_data):
        # Get the current authenticated user
        user = self.context['request'].user

        # Create the PrayerMethod instance with the user instance
        prayer_method = PrayerMethod.objects.create(
            sn=validated_data['sn'],
            name=validated_data['name'],
            user=user
        )
        return prayer_method
    
    def update(self, instance, validated_data):
        # Get the current authenticated user
        user = self.context['request'].user

        # Update the PrayerMethod instance with the user instance
        instance.sn = validated_data.get('sn', instance.sn)
        instance.name = validated_data.get('name', instance.name)
        instance.user = user
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
