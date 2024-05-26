from rest_framework import serializers
from .models import UserPreferences, PrayerMethod, PrayerOffset, CustomUser
from rest_auth.serializers import UserDetailsSerializer
from rest_auth.registration.serializers import RegisterSerializer


class CustomUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(read_only=True)
    # is_superuser = serializers.BooleanField(read_only=True)
    class Meta:
        model = CustomUser
        exclude = ('is_superuser', 'is_staff', 'is_active', 
                   'last_login', 'date_joined', 'groups', 'user_permissions')


class CustomUserDetailsSerializer(UserDetailsSerializer):
    class Meta(UserDetailsSerializer.Meta):
        model = CustomUser
        fields = UserDetailsSerializer.Meta.fields + ('sex', 'address', 'city', 'country', 'timezone', 'phone_number')
        read_only_fields = ('email',)


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = ['daily_prayer_summary_enabled', 'daily_prayer_summary_message_method', 'notification_before_prayer_enabled', 'notification_before_prayer', 'notification_time_before_prayer', 'adhan_call_enabled', 'adhan_call_method', 'notification_methods']


class PrayerMethodGenSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    class Meta:
        model = PrayerMethod
        # fields = '__all__'
        fields = ['id', 'user', 'name', 'sn']


class PrayerMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerMethod
        # exclude = ['user']
        fields = ['sn', 'name']

class PrayerOffsetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrayerOffset
        fields = '__all__'
        


class CustomRegisterSerializer(RegisterSerializer):
    sex = serializers.CharField(max_length=10, required=False)
    address = serializers.CharField(max_length=255, required=False)
    city = serializers.CharField(max_length=100, required=False)
    country = serializers.CharField(max_length=100, required=False)
    timezone = serializers.CharField(max_length=100, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)

    user_preferences = UserPreferencesSerializer(required=False)
    prayer_method = PrayerMethodSerializer(required=False)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['sex'] = self.validated_data.get('sex', '')
        data['address'] = self.validated_data.get('address', '')
        data['city'] = self.validated_data.get('city', '')
        data['country'] = self.validated_data.get('country', '')
        data['timezone'] = self.validated_data.get('timezone', '')
        data['phone_number'] = self.validated_data.get('phone_number', '')
        return data

    def save(self, request):
        user = super().save(request)
        user.sex = self.cleaned_data.get('sex')
        user.address = self.cleaned_data.get('address')
        user.city = self.cleaned_data.get('city')
        user.country = self.cleaned_data.get('country')
        user.timezone = self.cleaned_data.get('timezone')
        user.phone_number = self.cleaned_data.get('phone_number')
        user.save()

        user_preferences_data = self.validated_data.get('user_preferences')
        if user_preferences_data:
            UserPreferences.objects.create(user=user, **user_preferences_data)
            # preferences, _ = UserPreferences.objects.get_or_create(user=user)
            # for key, value in user_preferences_data.items():
            #     setattr(preferences, key, value)
            # preferences.save()

        prayer_method_data = self.validated_data.get('prayer_method')
        if prayer_method_data:
            PrayerMethod.objects.create(user=user, **prayer_method_data)
            # prayer_method, _ = PrayerMethod.objects.get_or_create(user=user)
            # for key, value in prayer_method_data.items():
            #     setattr(prayer_method, key, value)
            # prayer_method.save()

        return user
