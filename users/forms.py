from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from .models import CustomUser, Location, PrayerMethod, SubscriptionTier, UserPreferences
from zoneinfo import available_timezones


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            widget = self.fields[field].widget
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.Select)):
                widget.attrs.update({'class': 'form-control'})
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(widget, forms.RadioSelect):
                widget.attrs.update({'class': 'form-check-input'})


class CustomUserCreationForm(UserCreationForm):
    # Get all available timezones
    TIMEZONE_CHOICES = [(tz, tz) for tz in sorted(available_timezones())]
    # If using pytz: TIMEZONE_CHOICES = [(tz, tz) for tz in sorted(common_timezones)]

    # Override the timezone field to use a dropdown
    timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = UserCreationForm.Meta.fields + ('email', 'sex', 'address', 'city', 'country', 'timezone', 'phone_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set a default timezone if desired
        self.fields['timezone'].initial = 'Africa/Lagos'


class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = CustomUser


class CustomUserChangeForm(UserChangeForm):
    TIMEZONE_CHOICES = [(tz, tz) for tz in sorted(available_timezones())]
    timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES)

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'sex', 'address', 'city', 'country', 'timezone', 'phone_number')


class UserPreferencesForm(BootstrapModelForm):
    class Meta:
        model = UserPreferences
        fields = [
            'subscription_tier',
            'daily_prayer_summary_enabled',
            'daily_prayer_summary_message_method',
            'pre_prayer_reminder_enabled',
            'pre_prayer_reminder_method',
            'pre_prayer_reminder_time',
            'adhan_call_enabled',
            'fajr_reminder_enabled',
            'zuhr_reminder_enabled',
            'asr_reminder_enabled',
            'maghrib_reminder_enabled',
            'isha_reminder_enabled',
            'fajr_adhan_call_enabled',
            'zuhr_adhan_call_enabled',
            'asr_adhan_call_enabled',
            'maghrib_adhan_call_enabled',
            'isha_adhan_call_enabled',
        ]
        widgets = {
            'subscription_tier': forms.RadioSelect(),
            'daily_summary_method': forms.Select(),
            'pre_prayer_reminder_method': forms.Select(),
            'pre_prayer_reminder_time': forms.NumberInput(attrs={'min': 1, 'max': 60}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subscription_tier'].queryset = SubscriptionTier.objects.all()

        if self.instance.subscription_tier:
            if self.instance.subscription_tier.name == "Base Plan":
                self._disable_enhanced_premium_fields()
            elif self.instance.subscription_tier.name == "Enhanced Plan":
                self._disable_premium_fields()

    def _disable_enhanced_premium_fields(self):
        for field in ['pre_prayer_reminder_enabled', 'pre_prayer_reminder_method', 'pre_prayer_reminder_time',
                      'adhan_call_enabled', 'fajr_reminder_enabled', 'zuhr_reminder_enabled', 'asr_reminder_enabled',
                      'maghrib_reminder_enabled', 'isha_reminder_enabled', 'fajr_adhan_call_enabled',
                      'zuhr_adhan_call_enabled', 'asr_adhan_call_enabled', 'maghrib_adhan_call_enabled',
                      'isha_adhan_call_enabled']:
            self.fields[field].widget.attrs['disabled'] = True

    def _disable_premium_fields(self):
        for field in ['adhan_call_enabled', 'fajr_adhan_call_enabled', 'zuhr_adhan_call_enabled',
                      'asr_adhan_call_enabled', 'maghrib_adhan_call_enabled', 'isha_adhan_call_enabled']:
            self.fields[field].widget.attrs['disabled'] = True
        self.fields['pre_prayer_reminder_method'].choices = [
            choice for choice in self.fields['pre_prayer_reminder_method'].choices if choice[0] != 'sms'
        ]


    def _disable_enhanced_premium_fields(self):
        for field in ['pre_prayer_reminder_enabled', 'pre_prayer_reminder_method', 'pre_prayer_reminder_time',
                      'adhan_call_enabled', 'fajr_reminder_enabled', 'zuhr_reminder_enabled', 'asr_reminder_enabled',
                      'maghrib_reminder_enabled', 'isha_reminder_enabled', 'fajr_adhan_call_enabled',
                      'zuhr_adhan_call_enabled', 'asr_adhan_call_enabled', 'maghrib_adhan_call_enabled',
                      'isha_adhan_call_enabled']:
            self.fields[field].widget.attrs['disabled'] = True

    def _disable_premium_fields(self):
        for field in ['adhan_call_enabled', 'fajr_adhan_call_enabled', 'zuhr_adhan_call_enabled',
                      'asr_adhan_call_enabled', 'maghrib_adhan_call_enabled', 'isha_adhan_call_enabled']:
            self.fields[field].widget.attrs['disabled'] = True
        self.fields['pre_prayer_reminder_method'].choices = [
            choice for choice in self.fields['pre_prayer_reminder_method'].choices if choice[0] != 'sms'
        ]


# class SubscriptionUpgradeForm(forms.Form):
#     new_tier = forms.ModelChoiceField(queryset=SubscriptionTier.objects.all(), widget=forms.RadioSelect)

    
class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        exclude = ['user']

class PrayerMethodForm(forms.ModelForm):
    sn = forms.ChoiceField(choices=PrayerMethod.METHOD_CHOICES, label="Prayer Calculation Method")

    class Meta:
        model = PrayerMethod
        fields = ['sn']
        # exclude = ['user']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.name = dict(PrayerMethod.METHOD_CHOICES).get(int(instance.sn), "Unknown Method")
        if commit:
            instance.save()
        return instance


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = [
            'daily_prayer_summary_enabled',
            'daily_prayer_summary_message_method',
            'pre_prayer_reminder_enabled',
            'pre_prayer_reminder_method',
            'pre_prayer_reminder_time',
            'adhan_call_enabled',
            'adhan_call_method',
            'notification_methods',
        ]
        widgets = {
            'daily_prayer_summary_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_before_prayer_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'adhan_call_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_time_before_prayer': forms.NumberInput(attrs={'min': 0, 'max': 60, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if not isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({'class': 'form-control'})


class SubscriptionUpgradeForm(forms.Form):
    new_tier = forms.ModelChoiceField(
        queryset=SubscriptionTier.objects.all(),
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )