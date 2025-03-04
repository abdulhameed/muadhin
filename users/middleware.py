from django.shortcuts import redirect
from django.urls import reverse
from .models import UserPreferences, Location, PrayerMethod


class StepCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_path = request.path_info
            
            if current_path == reverse('step2_location'):
                if not UserPreferences.objects.filter(user=request.user, is_completed=True).exists():
                    return redirect('step1_user_preferences')
            
            elif current_path == reverse('step3_prayer_method'):
                if not UserPreferences.objects.filter(user=request.user, is_completed=True).exists():
                    return redirect('step1_user_preferences')
                elif not Location.objects.filter(user=request.user, is_completed=True).exists():
                    return redirect('step2_location')

        response = self.get_response(request)
        return response
    