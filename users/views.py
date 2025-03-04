from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage, send_mail
from .forms import CustomUserChangeForm, CustomUserCreationForm, CustomAuthenticationForm, LocationForm, PrayerMethodForm, SubscriptionUpgradeForm, UserPreferencesForm
from django.conf import settings
from .models import CustomUser, AuthToken, Location, PrayerMethod, UserPreferences
from .tokens import account_activation_token
from django.contrib.auth import get_user_model
import uuid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.decorators import login_required
from django.contrib import messages

user = get_user_model()


def homepage(request):
    return render(request, 'users/homepage.html')


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'users/signup.html'

    def form_valid(self, form):
        # Save the user, but don't commit to database yet
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # Generate the activation token
        token = account_activation_token.make_token(user)

        # Create activation link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        activation_link = self.request.build_absolute_uri(
            reverse('activate-account', args=[uid, token])
        )

        # Send activation email
        send_mail(
            'Activate Your Account',
            f'Please click the following link to activate your account: {activation_link}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        # Render a template to inform the user
        return render(self.request, 'users/account_activation_sent.html')

    # def form_valid(self, form):
    #     user = form.save(commit=False)
    #     user.is_active = False
    #     user.save()

    #     current_site = get_current_site(self.request)
    #     mail_subject = 'Activate your account'
    #     message = render_to_string('users/account_activation_email.html', {
    #         'user': user,
    #         'domain': current_site.domain,
    #         'uid': urlsafe_base64_encode(force_bytes(user.pk)),
    #         'token': account_activation_token.make_token(user),
    #     })
    #     to_email = form.cleaned_data.get('email')
    #     email = EmailMessage(mail_subject, message, to=[to_email])
    #     email.send()

    #     return render(self.request, 'users/account_activation_sent.html')


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('dashboard')

    def get_success_url(self):
        return self.success_url


def activate_account(request, uidb64, token):
    User = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        # Activation successful
        return redirect('login')
    else:
        # Activation failed
        return render(request, 'users/activation_invalid.html')

# def activate(request, uidb64, token):
#     try:
#         uid = force_str(urlsafe_base64_decode(uidb64))
#         user = CustomUser.objects.get(pk=uid)
#     except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
#         user = None
#     if user is not None and account_activation_token.check_token(user, token):
#         user.is_active = True
#         user.save()
#         login(request, user)
#         return redirect('home')
#     else:
#         return render(request, 'users/account_activation_invalid.html')
    

class CustomUserUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserChangeForm
    template_name = 'users/user_profile.html'
    success_url = reverse_lazy('user_detail')

    def get_object(self, queryset=None):
        return self.request.user

class UserPreferencesCreateView(LoginRequiredMixin, CreateView):
    model = UserPreferences
    form_class = UserPreferencesForm
    template_name = 'users/preferences_form.html'
    success_url = reverse_lazy('user_detail')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class UserPreferencesUpdateView(LoginRequiredMixin, UpdateView):
    model = UserPreferences
    form_class = UserPreferencesForm
    template_name = 'users/preferences_form.html'
    success_url = reverse_lazy('user_detail')

    def get_object(self, queryset=None):
        return self.request.user.userpreferences


@login_required
def upgrade_subscription(request):
    user_prefs = UserPreferences.objects.get(user=request.user)
    if request.method == 'POST':
        form = SubscriptionUpgradeForm(request.POST)
        if form.is_valid():
            new_tier = form.cleaned_data['new_tier']
            user_prefs.subscription_tier = new_tier
            user_prefs.save()
            return redirect('user_preferences')
    else:
        form = SubscriptionUpgradeForm(initial={'new_tier': user_prefs.subscription_tier})
    return render(request, 'upgrade_subscription.html', {'form': form})


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = 'users/location_settings.html'
    success_url = reverse_lazy('user_detail')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class LocationUpdateView(LoginRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = 'users/location_settings.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self, queryset=None):
        try:
            return self.request.user.location
        except Location.DoesNotExist:
            # Create a new Location object for the user
            location = Location(user=self.request.user)
            location.save()
            return location

    def form_valid(self, form):
        messages.success(self.request, 'Location updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error updating location. Please check the form.')
        return super().form_invalid(form)

class PrayerMethodCreateView(LoginRequiredMixin, CreateView):
    model = PrayerMethod
    form_class = PrayerMethodForm
    template_name = 'users/prayer_method_settings.html'
    success_url = reverse_lazy('user_detail')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class PrayerMethodUpdateView(LoginRequiredMixin, UpdateView):
    model = PrayerMethod
    form_class = PrayerMethodForm
    template_name = 'users/prayer_method_settings.html'
    success_url = reverse_lazy('user_detail')

    def get_object(self, queryset=None):
        return self.request.user.prayermethod


# @login_required
# def user_preferences(request):
#     try:
#         user_pref = UserPreferences.objects.get(user=request.user)
#     except UserPreferences.DoesNotExist:
#         user_pref = UserPreferences(user=request.user)
#         user_pref.save()

#     if request.method == 'POST':
#         form = UserPreferencesForm(request.POST, instance=user_pref)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Your preferences have been updated.')
#             return redirect('user_preferences')
#     else:
#         form = UserPreferencesForm(instance=user_pref)

#     return render(request, 'users/preferences.html', {'form': form})


@login_required
def user_preferences(request):
    user_prefs, created = UserPreferences.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=user_prefs)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your preferences have been updated.')
            return redirect('user_preferences')
    else:
        form = UserPreferencesForm(instance=user_prefs)
    return render(request, 'users/preferences.html', {'form': form})


##########################################
@login_required
def step1_user_preferences(request):
    try:
        instance = UserPreferences.objects.get(user=request.user)
    except UserPreferences.DoesNotExist:
        instance = None

    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=instance)
        if form.is_valid():
            preferences = form.save(commit=False)
            preferences.user = request.user
            preferences.is_completed = True
            preferences.save()
            return redirect('step2_location')
    else:
        form = UserPreferencesForm(instance=instance)

    return render(request, 'users/step1_user_preferences.html', {'form': form})

@login_required
def step2_location(request):
    try:
        instance = Location.objects.get(user=request.user)
    except Location.DoesNotExist:
        instance = None

    if request.method == 'POST':
        form = LocationForm(request.POST, instance=instance)
        if form.is_valid():
            location = form.save(commit=False)
            location.user = request.user
            location.is_completed = True
            location.save()
            return redirect('step3_prayer_method')
    else:
        form = LocationForm(instance=instance)

    return render(request, 'users/step2_location.html', {'form': form})

@login_required
def step3_prayer_method(request):
    try:
        instance = PrayerMethod.objects.get(user=request.user)
    except PrayerMethod.DoesNotExist:
        instance = None

    if request.method == 'POST':
        print(f"=========>>>>>>> Entering Form POST method")
        form = PrayerMethodForm(request.POST, instance=instance)
        print(f"=========>>>>>>> Before Form Valid Block")
        if form.is_valid():
            print(f"=========>>>>>>> Entering Form Valid Block")
            prayer_method = form.save(commit=False)
            prayer_method.user = request.user
            prayer_method.is_completed = True
            prayer_method.save()
            print(f"=========||||||>>>>>>> Redirecting to Setup Complete fxn <<<<<<<<<<<<<<<<<|||||||||====================")
            return redirect('setup_completed')
        else:
            print("Form is not valid. Errors:")
            print(form.errors)
            print("POST data:")
            print(request.POST)
    else:
        form = PrayerMethodForm(instance=instance)

    return render(request, 'users/step3_prayer_method.html', {'form': form})


def all_steps_completed(user):
    return all([
        UserPreferences.objects.filter(user=user, is_completed=True).exists(),
        Location.objects.filter(user=user, is_completed=True).exists(),
        PrayerMethod.objects.filter(user=user, is_completed=True).exists()
    ])


def reset_setup(request):
    UserPreferences.objects.filter(user=request.user).update(is_completed=False)
    Location.objects.filter(user=request.user).update(is_completed=False)
    PrayerMethod.objects.filter(user=request.user).update(is_completed=False)
    return redirect('step1_user_preferences')


@login_required
def setup_completed(request):
    User = request.user
    # Check if all steps are actually completed
    user_preferences = UserPreferences.objects.filter(user=User, is_completed=True).exists()
    location = Location.objects.filter(user=User, is_completed=True).exists()
    prayer_method = PrayerMethod.objects.filter(user=User, is_completed=True).exists()

    if not (user_preferences and location and prayer_method):
        # If any step is not completed, redirect to the appropriate step
        if not user_preferences:
            return redirect('step1_user_preferences')
        elif not location:
            return redirect('step2_location')
        elif not prayer_method:
            return redirect('step3_prayer_method')
        
     # Update the user's setup_completed field
    User.setup_completed = True
    User.save()

    # If all steps are completed, render the completion page
    return render(request, 'users/setup_completed.html')
