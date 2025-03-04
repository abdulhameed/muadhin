from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date
# Import your prayer time calculation function here
# from .utils import calculate_prayer_times

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'SalatTracker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        # Calculate prayer times for the current day
        # You'll need to implement this function based on your specific requirements
        # prayer_times = calculate_prayer_times(user.location, user.prayermethod, today)

        # For demonstration, let's use dummy data
        prayer_times = {
            'Fajr': '05:30',
            'Dhuhr': '12:30',
            'Asr': '15:45',
            'Maghrib': '18:30',
            'Isha': '20:00'
        }

        context['prayer_times'] = prayer_times
        return context
    

class NewDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'SalatTracker/new_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        # Calculate prayer times for the current day
        # You'll need to implement this function based on your specific requirements
        # prayer_times = calculate_prayer_times(user.location, user.prayermethod, today)

        # For demonstration, let's use dummy data
        prayer_times = {
            'Fajr': '05:30',
            'Dhuhr': '12:30',
            'Asr': '15:45',
            'Maghrib': '18:30',
            'Isha': '20:00'
        }

        context['prayer_times'] = prayer_times
        return context
