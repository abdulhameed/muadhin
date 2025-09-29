import uuid
import logging
from rest_framework import viewsets, generics, permissions
from django.contrib.auth.tokens import default_token_generator

from django.core.mail import send_mail
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from subscriptions.services.subscription_service import SubscriptionService
from .permissions import IsOwnerOrReadOnly
from .models import CustomUser, UserPreferences, PrayerMethod, PrayerOffset, AuthToken
from .serializers import UserPreferencesSerializer, PrayerMethodSerializer, PrayerOffsetSerializer, CustomUserSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.conf import settings
import pytz
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes, permission_classes
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.decorators import action
from .services.location_service import LocationService

# Configure logger for this module
logger = logging.getLogger(__name__)


User = get_user_model()

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate and store the activation token
        token = str(uuid.uuid4())
        print(f"Generated token >>>>>>>>>>: {token}")
        auth_token = AuthToken.objects.create(user=user, token=token)
        print(f"Created AuthToken instance >>>>>>>>>>>: {auth_token}")

        # Send email activation link
        # token = default_token_generator.make_token(user)
        activation_link = request.build_absolute_uri(reverse('activate-account', args=[token]))
        send_mail(
            'Activate Your Account',
            f'Please click the following link to activate your account: {activation_link}',
            # Your email settings
            settings.EMAIL_HOST_USER,  # Set your default from email here
            [user.email],  # List of recipient email addresses
            fail_silently=False,
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AccountActivationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    # permission_classes = [AllowAny]

    def get_serializer_class(self):
        return None
    
    def get_serializer(self, *args, **kwargs):
        return None
    
    def get(self, request, token):
        try:
            auth_token = AuthToken.objects.get(token=token)
            user = auth_token.user
            # user = CustomUser.objects.get(is_active=False, auth_token__token=token)
        # except CustomUser.DoesNotExist:
        except AuthToken.DoesNotExist:
            return Response({'error': 'Invalid activation link'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.is_active:
            return Response({'success': 'Account is already activated'}, status=status.HTTP_200_OK)

        user.is_active = True
        user.save()
        auth_token.delete()  # Delete the activation token after successful activation
        return Response({'success': 'Account activated successfully'}, status=status.HTTP_200_OK)

#   TODO FIX
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def ResendActivationEmailView(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)

    if user.is_active:
        return Response({'error': 'User account is already activated'}, status=status.HTTP_400_BAD_REQUEST)

    # Generate and store a new activation token
    token = str(uuid.uuid4())
    AuthToken.objects.filter(user=user).delete()  # Delete any existing tokens
    auth_token = AuthToken.objects.create(user=user, token=token)

    # Send email activation link
    activation_link = request.build_absolute_uri(reverse('activate-account', args=[token]))
    send_mail(
        'Activate Your Account',
        f'Please click the following link to activate your account: {activation_link}',
        settings.EMAIL_HOST_USER,
        [user.email],
        fail_silently=False,
    )

    return Response({'success': 'Activation email has been resent'}, status=status.HTTP_200_OK)


class PasswordResetView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        return None
    
    def get_serializer(self, *args, **kwargs):
        return None
    
    def post(self, request):
        email = request.data.get('email')
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)

        # Send password reset email
        token = default_token_generator.make_token(user)
        reset_link = request.build_absolute_uri(reverse('reset-password', args=[token]))
        send_mail(
            'Reset Your Password',
            f'Please click the following link to reset your password: {reset_link}',
            # Your email settings
            fail_silently=False,
        )

        return Response({'success': 'Password reset link has been sent to your email'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        return None
    
    def get_serializer(self, *args, **kwargs):
        return None
    
    def post(self, request, token):
        try:
            user = CustomUser.objects.get(auth_token__token=token)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)

        new_password = request.data.get('new_password')
        user.set_password(new_password)
        user.save()
        return Response({'success': 'Password reset successful'}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data) 
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    

class UserPreferencesViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user preferences with proper security and user filtering
    """
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only return the current user's preferences"""
        return UserPreferences.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Automatically set the user when creating preferences"""
        serializer.save(user=self.request.user)
    
    def get_object(self):
        """Get the user's preferences or create if they don't exist"""
        try:
            return self.get_queryset().get()
        except UserPreferences.DoesNotExist:
            # Auto-create preferences with defaults if they don't exist
            return UserPreferences.objects.create(
                user=self.request.user,
                daily_prayer_summary_enabled=True,
                daily_prayer_summary_message_method='email',
                notification_before_prayer_enabled=True,
                notification_before_prayer='email',
                notification_time_before_prayer=15,
                adhan_call_enabled=True,
                adhan_call_method='email',
                notification_methods='email',
            )
    
    @action(detail=False, methods=['get'])
    def my_preferences(self, request):
        """Get current user's preferences - creates if doesn't exist"""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch', 'put'])
    def update_my_preferences(self, request):
        """Update current user's preferences"""
        preferences = self.get_object()
        serializer = self.get_serializer(
            preferences, 
            data=request.data, 
            partial=(request.method == 'PATCH')
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def available_options(self, request):
        """Get available notification options based on user's subscription plan"""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        
        # The serializer already includes available options based on subscription
        return Response({
            'current_preferences': serializer.data,
            'available_daily_summary_methods': serializer.data.get('available_daily_summary_methods', []),
            'available_pre_adhan_methods': serializer.data.get('available_pre_adhan_methods', []),
            'available_adhan_call_methods': serializer.data.get('available_adhan_call_methods', []),
            'current_plan': serializer.data.get('current_plan', {}),
        })
    
    def list(self, request):
        """Override list to return only current user's preferences"""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        return Response([serializer.data])  # Return as list for consistency
    
    def retrieve(self, request, pk=None):
        """Override retrieve to always return current user's preferences"""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)


class PrayerMethodViewSet(viewsets.ModelViewSet):
    queryset = PrayerMethod.objects.all()
    serializer_class = PrayerMethodSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    

# class PrayerMethodViewSet(viewsets.ModelViewSet):
#     queryset = PrayerMethod.objects.all()
#     serializer_class = PrayerMethodSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

class PrayerOffsetViewSet(viewsets.ModelViewSet):
    queryset = PrayerOffset.objects.all()
    serializer_class = PrayerOffsetSerializer


def create_admin_view(request):
    username = 'admin3'
    email = 'admin3@example1.com'
    password = 'admin123456'
    
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        return HttpResponse(f'Admin user "{username}" created successfully!')
    else:
        return HttpResponse(f'Admin user "{username}" already exists')
    

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT login view that includes user information in the response
    """
    serializer_class = CustomTokenObtainPairSerializer


class NotificationSettingsAPIView(APIView):
    """
    Comprehensive endpoint for managing all notification settings
    
    GET: Returns current notification settings with availability info
    PATCH: Updates notification settings (partial updates allowed)
    PUT: Updates all notification settings (full update)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current notification settings with subscription info"""
        user = request.user
        
        # Get or create user preferences
        preferences = self._get_or_create_preferences(user)
        
        # Get subscription info
        current_plan = SubscriptionService.get_user_plan(user)
        subscription_info = self._get_subscription_info(user, current_plan)
        
        # Get available options for each notification type
        available_options = self._get_available_options(user)
        
        # Build current settings
        current_settings = {
            'daily_summary': {
                'enabled': preferences.daily_prayer_summary_enabled,
                'method': preferences.daily_prayer_summary_message_method,
                'description': 'Get today\'s prayer times once per day (sent at morning)',
                'frequency': 'Once daily'
            },
            'pre_adhan_reminders': {
                'enabled': preferences.notification_before_prayer_enabled,
                'method': preferences.notification_before_prayer,
                'timing_minutes': preferences.notification_time_before_prayer,
                'description': 'Get notified before each prayer time (5 notifications per day)',
                'frequency': '5 times daily'
            },
            'adhan_calls': {
                'enabled': preferences.adhan_call_enabled,
                'method': preferences.adhan_call_method,
                'description': 'Get notified exactly at prayer time (5 notifications per day)',
                'frequency': '5 times daily'
            }
        }
        
        return Response({
            'user_info': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'phone_number': user.phone_number,
                'whatsapp_number': getattr(user, 'whatsapp_number', None)
            },
            'subscription': subscription_info,
            'current_settings': current_settings,
            'available_options': available_options,
            'validation_info': self._get_validation_info(user),
            'total_daily_notifications': self._calculate_daily_notifications(preferences)
        })
    
    def patch(self, request):
        """Partially update notification settings"""
        return self._update_settings(request, partial=True)
    
    def put(self, request):
        """Fully update notification settings"""
        return self._update_settings(request, partial=False)
    
    def _update_settings(self, request, partial=True):
        """Handle settings updates"""
        user = request.user
        preferences = self._get_or_create_preferences(user)
        
        # Extract settings from request data
        settings_data = {}
        errors = {}
        warnings = []
        
        # Process daily summary settings
        if 'daily_summary' in request.data:
            daily_data = request.data['daily_summary']
            if 'enabled' in daily_data:
                settings_data['daily_prayer_summary_enabled'] = daily_data['enabled']
            if 'method' in daily_data:
                method = daily_data['method']
                if self._validate_notification_method(user, 'daily_prayer_summary', method):
                    settings_data['daily_prayer_summary_message_method'] = method
                else:
                    errors['daily_summary_method'] = f'Method "{method}" not available in your current plan'
        
        # Process pre-adhan reminder settings
        if 'pre_adhan_reminders' in request.data:
            pre_adhan_data = request.data['pre_adhan_reminders']
            if 'enabled' in pre_adhan_data:
                settings_data['notification_before_prayer_enabled'] = pre_adhan_data['enabled']
            if 'method' in pre_adhan_data:
                method = pre_adhan_data['method']
                if self._validate_notification_method(user, 'pre_adhan', method):
                    settings_data['notification_before_prayer'] = method
                else:
                    errors['pre_adhan_method'] = f'Method "{method}" not available in your current plan'
            if 'timing_minutes' in pre_adhan_data:
                timing = pre_adhan_data['timing_minutes']
                if 1 <= timing <= 60:
                    settings_data['notification_time_before_prayer'] = timing
                else:
                    errors['timing_minutes'] = 'Timing must be between 1 and 60 minutes'
        
        # Process adhan call settings
        if 'adhan_calls' in request.data:
            adhan_data = request.data['adhan_calls']
            if 'enabled' in adhan_data:
                settings_data['adhan_call_enabled'] = adhan_data['enabled']
            if 'method' in adhan_data:
                method = adhan_data['method']
                if self._validate_notification_method(user, 'adhan_call', method):
                    settings_data['adhan_call_method'] = method
                else:
                    errors['adhan_method'] = f'Method "{method}" not available in your current plan'
        
        # Return errors if any validation failed
        if errors:
            return Response({
                'success': False,
                'errors': errors,
                'message': 'Some settings could not be updated due to validation errors',
                'available_options': self._get_available_options(user),
                'upgrade_info': self._get_upgrade_info(user)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update preferences
        try:
            serializer = UserPreferencesSerializer(
                preferences, 
                data=settings_data, 
                partial=partial,
                context={'request': request}
            )
            
            if serializer.is_valid():
                updated_preferences = serializer.save()
                
                # Check for plan limitations and add warnings
                warnings = self._get_plan_warnings(user, updated_preferences)
                
                return Response({
                    'success': True,
                    'message': 'Notification settings updated successfully',
                    'warnings': warnings,
                    'updated_settings': self._format_current_settings(updated_preferences),
                    'total_daily_notifications': self._calculate_daily_notifications(updated_preferences),
                    'next_steps': self._get_next_steps(user, updated_preferences)
                })
            else:
                return Response({
                    'success': False,
                    'errors': serializer.errors,
                    'message': 'Validation failed'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'An error occurred while updating settings'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_or_create_preferences(self, user):
        """Get or create user preferences"""
        try:
            return user.preferences
        except UserPreferences.DoesNotExist:
            return UserPreferences.objects.create(
                user=user,
                daily_prayer_summary_enabled=True,
                daily_prayer_summary_message_method='email',
                notification_before_prayer_enabled=True,
                notification_before_prayer='email',
                notification_time_before_prayer=15,
                adhan_call_enabled=True,
                adhan_call_method='email',
                notification_methods='email',
            )
    
    def _get_subscription_info(self, user, current_plan):
        """Get subscription information"""
        try:
            subscription = getattr(user, 'subscription', None)
            if subscription:
                return {
                    'plan_name': current_plan.name,
                    'plan_type': current_plan.plan_type,
                    'price': float(current_plan.price),
                    'status': subscription.status,
                    'max_notifications_per_day': current_plan.max_notifications_per_day,
                    'features': current_plan.features_list
                }
        except:
            pass
        
        return {
            'plan_name': current_plan.name,
            'plan_type': current_plan.plan_type,
            'price': float(current_plan.price),
            'status': 'basic',
            'max_notifications_per_day': current_plan.max_notifications_per_day,
            'features': current_plan.features_list
        }
    
    def _get_available_options(self, user):
        """Get available notification options based on subscription"""
        daily_summary_options = []
        pre_adhan_options = []
        adhan_call_options = []
        
        # Check daily summary options
        for method, label in UserPreferences.NOTIFICATION_METHODS:
            is_available = SubscriptionService.validate_notification_preference(
                user, 'daily_prayer_summary', method
            )
            daily_summary_options.append({
                'value': method,
                'label': label,
                'available': is_available,
                'icon': self._get_method_icon(method),
                'upgrade_required': not is_available
            })
        
        # Check pre-adhan options
        for method, label in UserPreferences.NOTIFICATION_METHODS:
            is_available = SubscriptionService.validate_notification_preference(
                user, 'pre_adhan', method
            )
            pre_adhan_options.append({
                'value': method,
                'label': label,
                'available': is_available,
                'icon': self._get_method_icon(method),
                'upgrade_required': not is_available
            })
        
        # Check adhan call options
        for method, label in UserPreferences.ADHAN_METHODS:
            is_available = SubscriptionService.validate_notification_preference(
                user, 'adhan_call', method
            )
            adhan_call_options.append({
                'value': method,
                'label': label,
                'available': is_available,
                'icon': self._get_method_icon(method),
                'upgrade_required': not is_available
            })
        
        return {
            'daily_summary': daily_summary_options,
            'pre_adhan_reminders': pre_adhan_options,
            'adhan_calls': adhan_call_options,
            'timing_options': [
                {'value': 5, 'label': '5 minutes before'},
                {'value': 10, 'label': '10 minutes before'},
                {'value': 15, 'label': '15 minutes before'},
                {'value': 20, 'label': '20 minutes before'},
                {'value': 30, 'label': '30 minutes before'},
                {'value': 45, 'label': '45 minutes before'},
                {'value': 60, 'label': '1 hour before'},
            ]
        }
    
    def _validate_notification_method(self, user, notification_type, method):
        """Validate if user can use this notification method"""
        return SubscriptionService.validate_notification_preference(
            user, notification_type, method
        )
    
    def _get_method_icon(self, method):
        """Get icon for notification method"""
        icons = {
            'email': '📧',
            'sms': '📱',
            'whatsapp': '💬',
            'call': '📞',
            'text': '📝'
        }
        return icons.get(method, '❓')
    
    def _calculate_daily_notifications(self, preferences):
        """Calculate total daily notifications"""
        total = 0
        
        if preferences.daily_prayer_summary_enabled:
            total += 1  # Daily summary once per day
        
        if preferences.notification_before_prayer_enabled:
            total += 5  # Pre-adhan for 5 prayers
        
        if preferences.adhan_call_enabled:
            total += 5  # Adhan calls for 5 prayers
        
        return {
            'total': total,
            'breakdown': {
                'daily_summary': 1 if preferences.daily_prayer_summary_enabled else 0,
                'pre_adhan': 5 if preferences.notification_before_prayer_enabled else 0,
                'adhan_calls': 5 if preferences.adhan_call_enabled else 0
            }
        }
    
    def _format_current_settings(self, preferences):
        """Format current settings for response"""
        return {
            'daily_summary': {
                'enabled': preferences.daily_prayer_summary_enabled,
                'method': preferences.daily_prayer_summary_message_method,
                'icon': self._get_method_icon(preferences.daily_prayer_summary_message_method)
            },
            'pre_adhan_reminders': {
                'enabled': preferences.notification_before_prayer_enabled,
                'method': preferences.notification_before_prayer,
                'timing_minutes': preferences.notification_time_before_prayer,
                'icon': self._get_method_icon(preferences.notification_before_prayer)
            },
            'adhan_calls': {
                'enabled': preferences.adhan_call_enabled,
                'method': preferences.adhan_call_method,
                'icon': self._get_method_icon(preferences.adhan_call_method)
            }
        }
    
    def _get_plan_warnings(self, user, preferences):
        """Get warnings about plan limitations"""
        warnings = []
        current_plan = SubscriptionService.get_user_plan(user)
        
        # Check if user is using basic plan with limitations
        if current_plan.plan_type == 'basic':
            if preferences.daily_prayer_summary_message_method != 'email':
                warnings.append('Daily summary will use email fallback (Basic plan limitation)')
            if preferences.notification_before_prayer != 'email':
                warnings.append('Pre-adhan reminders will use email fallback (Basic plan limitation)')
            if preferences.adhan_call_method not in ['email', 'text']:
                warnings.append('Adhan calls will use email fallback (Basic plan limitation)')
        
        return warnings
    
    def _get_validation_info(self, user):
        """Get validation information for the frontend"""
        current_plan = SubscriptionService.get_user_plan(user)
        
        return {
            'plan_type': current_plan.plan_type,
            'max_daily_notifications': current_plan.max_notifications_per_day,
            'contact_info_required': {
                'email': bool(user.email),
                'phone_number': bool(user.phone_number),
                'whatsapp_number': bool(getattr(user, 'whatsapp_number', None))
            },
            'contact_info_missing': {
                'phone_number': not user.phone_number,
                'whatsapp_number': not getattr(user, 'whatsapp_number', None)
            }
        }
    
    def _get_upgrade_info(self, user):
        """Get upgrade information"""
        current_plan = SubscriptionService.get_user_plan(user)
        
        if current_plan.plan_type == 'basic':
            return {
                'suggested_plan': 'plus',
                'benefits': [
                    'WhatsApp notifications for daily summary',
                    'SMS and WhatsApp for pre-adhan reminders',
                    'Text message adhan calls',
                    'Increased daily notification limit'
                ],
                'upgrade_url': '/api/subscriptions/subscribe/',
                'message': 'Upgrade to Plus plan to unlock more notification methods'
            }
        elif current_plan.plan_type == 'plus':
            return {
                'suggested_plan': 'premium',
                'benefits': [
                    'Audio adhan calls',
                    'Custom adhan sounds',
                    'Unlimited daily notifications',
                    'Priority support'
                ],
                'upgrade_url': '/api/subscriptions/subscribe/',
                'message': 'Upgrade to Premium for the complete experience'
            }
        
        return None
    
    def _get_next_steps(self, user, preferences):
        """Get suggested next steps for user"""
        steps = []
        
        # Check for missing contact info
        if preferences.notification_before_prayer == 'sms' and not user.phone_number:
            steps.append({
                'action': 'add_phone_number',
                'message': 'Add phone number to receive SMS notifications',
                'url': '/api/users/profile/'
            })
        
        if preferences.daily_prayer_summary_message_method == 'whatsapp' and not getattr(user, 'whatsapp_number', None):
            steps.append({
                'action': 'add_whatsapp_number',
                'message': 'Add WhatsApp number to receive WhatsApp notifications',
                'url': '/api/users/profile/'
            })
        
        # Suggest testing notifications
        if any([preferences.daily_prayer_summary_enabled, 
                preferences.notification_before_prayer_enabled, 
                preferences.adhan_call_enabled]):
            steps.append({
                'action': 'test_notifications',
                'message': 'Test your notification settings',
                'url': '/api/notifications/test/'
            })
        
        return steps


class ProfileSettingsAPIView(APIView):
    """
    Comprehensive endpoint for managing all user profile settings
    
    GET: Returns current profile settings (location, contacts, preferences)
    PATCH: Updates profile settings (partial updates allowed)
    PUT: Updates all profile settings (full update)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current profile settings"""
        user = request.user
        
        # Get related objects
        preferences = self._get_or_create_preferences(user)
        prayer_method = self._get_or_create_prayer_method(user)
        prayer_offset = self._get_or_create_prayer_offset(user)
        
        # Build response
        return Response({
            'user_info': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'location_settings': {
                'city': user.city,
                'country': user.country,
                'timezone': user.timezone,
                'available_timezones': self._get_timezone_options()
            },
            'calculation_method': {
                'current_method': {
                    'id': prayer_method.sn,
                    'name': prayer_method.name,
                    'display_name': prayer_method.method_name
                },
                'available_methods': self._get_calculation_methods()
            },
            'reminder_settings': {
                'interval_minutes': preferences.notification_time_before_prayer,
                'available_intervals': [5, 10, 15, 20, 30, 45, 60]
            },
            'contact_information': {
                'phone_number': user.phone_number,
                'whatsapp_number': getattr(user, 'whatsapp_number', None),
                'twitter_handle': None,  # Add this field to CustomUser if needed
                'sms_number': user.phone_number,  # Usually same as phone
                'call_number': user.phone_number   # Usually same as phone
            },
            'display_preferences': {
                'show_last_third': getattr(preferences, 'show_last_third', False),  # Add this field if needed
            },
            'prayer_offsets': {
                'imsak': prayer_offset.imsak,
                'fajr': prayer_offset.fajr,
                'sunrise': prayer_offset.sunrise,
                'dhuhr': prayer_offset.dhuhr,
                'asr': prayer_offset.asr,
                'maghrib': prayer_offset.maghrib,
                'sunset': prayer_offset.sunset,
                'isha': prayer_offset.isha,
                'midnight': prayer_offset.midnight
            }
        })
    
    def patch(self, request):
        """Partially update profile settings"""
        return self._update_settings(request, partial=True)
    
    def put(self, request):
        """Fully update profile settings"""
        return self._update_settings(request, partial=False)
    
    def _update_settings(self, request, partial=True):
        """Handle settings updates"""
        user = request.user
        errors = {}
        updated_sections = []
        
        # Get related objects
        preferences = self._get_or_create_preferences(user)
        prayer_method = self._get_or_create_prayer_method(user)
        prayer_offset = self._get_or_create_prayer_offset(user)
        
        try:
            # Update location settings
            if 'location_settings' in request.data:
                location_data = request.data['location_settings']
                location_errors = self._update_location_settings(user, location_data)
                if location_errors:
                    errors['location_settings'] = location_errors
                else:
                    updated_sections.append('location')
            
            # Update calculation method
            if 'calculation_method' in request.data:
                method_data = request.data['calculation_method']
                method_errors = self._update_calculation_method(prayer_method, method_data)
                if method_errors:
                    errors['calculation_method'] = method_errors
                else:
                    updated_sections.append('calculation_method')
            
            # Update reminder settings
            if 'reminder_settings' in request.data:
                reminder_data = request.data['reminder_settings']
                reminder_errors = self._update_reminder_settings(preferences, reminder_data)
                if reminder_errors:
                    errors['reminder_settings'] = reminder_errors
                else:
                    updated_sections.append('reminder_settings')
            
            # Update contact information
            if 'contact_information' in request.data:
                contact_data = request.data['contact_information']
                contact_errors = self._update_contact_information(user, contact_data)
                if contact_errors:
                    errors['contact_information'] = contact_errors
                else:
                    updated_sections.append('contact_information')
            
            # Update display preferences
            if 'display_preferences' in request.data:
                display_data = request.data['display_preferences']
                display_errors = self._update_display_preferences(preferences, display_data)
                if display_errors:
                    errors['display_preferences'] = display_errors
                else:
                    updated_sections.append('display_preferences')
            
            # Update prayer offsets
            if 'prayer_offsets' in request.data:
                offset_data = request.data['prayer_offsets']
                offset_errors = self._update_prayer_offsets(prayer_offset, offset_data)
                if offset_errors:
                    errors['prayer_offsets'] = offset_errors
                else:
                    updated_sections.append('prayer_offsets')
            
            # Return errors if any validation failed
            if errors:
                return Response({
                    'success': False,
                    'errors': errors,
                    'message': 'Some settings could not be updated due to validation errors'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save all changes
            user.save()
            preferences.save()
            prayer_method.save()
            prayer_offset.save()
            
            return Response({
                'success': True,
                'message': 'Profile settings updated successfully',
                'updated_sections': updated_sections,
                'settings': self._build_current_settings(user, preferences, prayer_method, prayer_offset)
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'message': 'An error occurred while updating settings'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _update_location_settings(self, user, location_data):
        """Update location settings"""
        errors = {}
        
        if 'city' in location_data:
            city = location_data['city'].strip()
            if len(city) < 2:
                errors['city'] = 'City must be at least 2 characters long'
            else:
                user.city = city
        
        if 'country' in location_data:
            country = location_data['country'].strip()
            if len(country) < 2:
                errors['country'] = 'Country must be at least 2 characters long'
            else:
                user.country = country
        
        if 'timezone' in location_data:
            timezone = location_data['timezone']
            if timezone not in pytz.all_timezones:
                errors['timezone'] = 'Invalid timezone'
            else:
                user.timezone = timezone
        
        return errors
    
    def _update_calculation_method(self, prayer_method, method_data):
        """Update prayer calculation method"""
        errors = {}
        
        if 'method_id' in method_data:
            method_id = method_data['method_id']
            valid_methods = dict(PrayerMethod.METHOD_CHOICES)
            
            if method_id not in valid_methods:
                errors['method_id'] = 'Invalid calculation method'
            else:
                prayer_method.sn = method_id
                prayer_method.name = valid_methods[method_id]
        
        return errors
    
    def _update_reminder_settings(self, preferences, reminder_data):
        """Update reminder settings"""
        errors = {}
        
        if 'interval_minutes' in reminder_data:
            interval = reminder_data['interval_minutes']
            if not isinstance(interval, int) or interval < 1 or interval > 60:
                errors['interval_minutes'] = 'Interval must be between 1 and 60 minutes'
            else:
                preferences.notification_time_before_prayer = interval
        
        return errors
    
    def _update_contact_information(self, user, contact_data):
        """Update contact information"""
        errors = {}
        
        if 'phone_number' in contact_data:
            phone = contact_data['phone_number']
            if phone and not self._validate_phone_number(phone):
                errors['phone_number'] = 'Invalid phone number format'
            else:
                user.phone_number = phone
        
        if 'whatsapp_number' in contact_data:
            whatsapp = contact_data['whatsapp_number']
            if whatsapp and not self._validate_phone_number(whatsapp):
                errors['whatsapp_number'] = 'Invalid WhatsApp number format'
            else:
                user.whatsapp_number = whatsapp
        
        # Add twitter_handle field to CustomUser model if needed
        if 'twitter_handle' in contact_data:
            twitter = contact_data['twitter_handle']
            if twitter and not self._validate_twitter_handle(twitter):
                errors['twitter_handle'] = 'Invalid Twitter handle format'
            # else:
            #     user.twitter_handle = twitter  # Add this field to model
        
        return errors
    
    def _update_display_preferences(self, preferences, display_data):
        """Update display preferences"""
        errors = {}
        
        if 'show_last_third' in display_data:
            show_last_third = display_data['show_last_third']
            if not isinstance(show_last_third, bool):
                errors['show_last_third'] = 'Must be a boolean value'
            # else:
            #     preferences.show_last_third = show_last_third  # Add this field to model
        
        return errors
    
    def _update_prayer_offsets(self, prayer_offset, offset_data):
        """Update prayer time offsets"""
        errors = {}
        valid_prayers = ['imsak', 'fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'sunset', 'isha', 'midnight']
        
        for prayer in valid_prayers:
            if prayer in offset_data:
                offset_value = offset_data[prayer]
                if not isinstance(offset_value, int) or offset_value < -60 or offset_value > 60:
                    errors[prayer] = 'Offset must be between -60 and 60 minutes'
                else:
                    setattr(prayer_offset, prayer, offset_value)
        
        return errors
    
    def _validate_phone_number(self, phone):
        """Validate phone number format"""
        if not phone:
            return True  # Allow empty phone numbers
        
        # Basic validation - adjust regex as needed
        import re
        pattern = r'^\+?[\d\s\-\(\)]{8,20}$'
        return bool(re.match(pattern, phone))
    
    def _validate_twitter_handle(self, handle):
        """Validate Twitter handle format"""
        if not handle:
            return True
        
        import re
        # Twitter handle validation
        pattern = r'^@?[A-Za-z0-9_]{1,15}$'
        return bool(re.match(pattern, handle))
    
    def _get_or_create_preferences(self, user):
        """Get or create user preferences"""
        try:
            return user.preferences
        except UserPreferences.DoesNotExist:
            return UserPreferences.objects.create(
                user=user,
                daily_prayer_summary_enabled=True,
                daily_prayer_summary_message_method='email',
                notification_before_prayer_enabled=True,
                notification_before_prayer='email',
                notification_time_before_prayer=15,
                adhan_call_enabled=True,
                adhan_call_method='email'
            )
    
    def _get_or_create_prayer_method(self, user):
        """Get or create prayer method"""
        try:
            return user.prayer_method
        except PrayerMethod.DoesNotExist:
            return PrayerMethod.objects.create(
                user=user,
                sn=1,
                name='Muslim World League'
            )
    
    def _get_or_create_prayer_offset(self, user):
        """Get or create prayer offset"""
        try:
            return user.prayer_offset
        except PrayerOffset.DoesNotExist:
            return PrayerOffset.objects.create(
                user=user,
                imsak=0, fajr=0, sunrise=0, dhuhr=0, asr=0,
                maghrib=0, sunset=0, isha=0, midnight=0
            )
    
    def _get_timezone_options(self):
        """Get available timezone options"""
        # Common timezones - you can expand this list
        common_timezones = [
            'Africa/Lagos',
            'Africa/Cairo',
            'Asia/Dubai',
            'Asia/Karachi',
            'Asia/Jakarta',
            'Europe/London',
            'America/New_York',
            'America/Los_Angeles'
        ]
        
        return [
            {'value': tz, 'label': tz.replace('_', ' ')}
            for tz in common_timezones
        ]
    
    def _get_calculation_methods(self):
        """Get available calculation methods"""
        return [
            {'id': method_id, 'name': method_name}
            for method_id, method_name in PrayerMethod.METHOD_CHOICES
        ]
    
    def _build_current_settings(self, user, preferences, prayer_method, prayer_offset):
        """Build current settings response"""
        return {
            'location': {
                'city': user.city,
                'country': user.country,
                'timezone': user.timezone
            },
            'calculation_method': {
                'id': prayer_method.sn,
                'name': prayer_method.method_name
            },
            'reminder_interval': preferences.notification_time_before_prayer,
            'contacts': {
                'phone_number': user.phone_number,
                'whatsapp_number': getattr(user, 'whatsapp_number', None)
            },
            'prayer_offsets': {
                'fajr': prayer_offset.fajr,
                'dhuhr': prayer_offset.dhuhr,
                'asr': prayer_offset.asr,
                'maghrib': prayer_offset.maghrib,
                'isha': prayer_offset.isha
            }
        }
    

class TimezonesAPIView(APIView):
    """
    API endpoint to get all available timezones
    Cached for 24 hours since timezones rarely change
    """
    permission_classes = [AllowAny]  # Public endpoint
    
    @method_decorator(cache_page(60 * 60 * 24))  # Cache for 24 hours
    def get(self, request):
        """Get all available timezones grouped by continent"""
        
        # Get filter parameter
        filter_type = request.query_params.get('filter', 'common')  # 'all', 'common', 'continent'
        continent = request.query_params.get('continent', None)
        
        if filter_type == 'all':
            timezones = self._get_all_timezones()
        elif filter_type == 'continent' and continent:
            timezones = self._get_timezones_by_continent(continent)
        else:  # default to common
            timezones = self._get_common_timezones()
        
        return Response({
            'timezones': timezones,
            'total_count': len(timezones),
            'filter_applied': filter_type,
            'available_filters': ['all', 'common', 'continent'],
            'available_continents': self._get_continents()
        })
    
    def _get_common_timezones(self):
        """Get commonly used timezones"""
        common_zones = [
            # Africa
            'Africa/Lagos', 'Africa/Cairo', 'Africa/Johannesburg', 'Africa/Nairobi',
            'Africa/Casablanca', 'Africa/Tunis', 'Africa/Algiers', 'Africa/Addis_Ababa',
            
            # Asia
            'Asia/Dubai', 'Asia/Karachi', 'Asia/Kolkata', 'Asia/Jakarta',
            'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Seoul', 'Asia/Singapore',
            'Asia/Bangkok', 'Asia/Manila', 'Asia/Riyadh', 'Asia/Tehran',
            
            # Europe
            'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Rome',
            'Europe/Madrid', 'Europe/Amsterdam', 'Europe/Brussels', 'Europe/Vienna',
            
            # Americas
            'America/New_York', 'America/Los_Angeles', 'America/Chicago', 'America/Denver',
            'America/Toronto', 'America/Vancouver', 'America/Mexico_City', 'America/Sao_Paulo',
            
            # Others
            'Australia/Sydney', 'Australia/Melbourne', 'Pacific/Auckland'
        ]
        
        return [
            {
                'value': tz,
                'label': self._format_timezone_label(tz),
                'continent': tz.split('/')[0] if '/' in tz else 'Other',
                'city': tz.split('/')[-1].replace('_', ' ') if '/' in tz else tz,
                'utc_offset': self._get_utc_offset(tz)
            }
            for tz in common_zones
        ]
    
    def _get_all_timezones(self):
        """Get all available timezones"""
        all_zones = list(pytz.all_timezones)
        
        return [
            {
                'value': tz,
                'label': self._format_timezone_label(tz),
                'continent': tz.split('/')[0] if '/' in tz else 'Other',
                'city': tz.split('/')[-1].replace('_', ' ') if '/' in tz else tz,
                'utc_offset': self._get_utc_offset(tz)
            }
            for tz in sorted(all_zones)
        ]
    
    def _get_timezones_by_continent(self, continent):
        """Get timezones for a specific continent"""
        continent_zones = [
            tz for tz in pytz.all_timezones 
            if tz.startswith(f"{continent}/")
        ]
        
        return [
            {
                'value': tz,
                'label': self._format_timezone_label(tz),
                'continent': continent,
                'city': tz.split('/')[-1].replace('_', ' '),
                'utc_offset': self._get_utc_offset(tz)
            }
            for tz in sorted(continent_zones)
        ]
    
    def _get_continents(self):
        """Get list of available continents"""
        continents = set()
        for tz in pytz.all_timezones:
            if '/' in tz:
                continent = tz.split('/')[0]
                continents.add(continent)
        
        return sorted(list(continents))
    
    def _format_timezone_label(self, timezone):
        """Format timezone for display"""
        if '/' not in timezone:
            return timezone
        
        parts = timezone.split('/')
        continent = parts[0]
        city = parts[-1].replace('_', ' ')
        
        # Add UTC offset for better UX
        utc_offset = self._get_utc_offset(timezone)
        
        return f"{city} ({continent}) - UTC{utc_offset}"
    
    def _get_utc_offset(self, timezone):
        """Get current UTC offset for timezone"""
        try:
            from datetime import datetime
            import pytz
            
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            offset = now.strftime('%z')
            
            if offset:
                # Format as +05:30 or -08:00
                return f"{offset[:3]}:{offset[3:]}"
            return "+00:00"
        except:
            return "+00:00"


# Add this endpoint for just getting user's current timezone info
class CurrentTimezoneAPIView(APIView):
    """Get current user's timezone information"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            import pytz
            from datetime import datetime
            
            user_tz = pytz.timezone(user.timezone)
            now = datetime.now(user_tz)
            
            return Response({
                'current_timezone': user.timezone,
                'formatted_name': user.timezone.replace('_', ' '),
                'continent': user.timezone.split('/')[0] if '/' in user.timezone else 'Other',
                'city': user.timezone.split('/')[-1].replace('_', ' ') if '/' in user.timezone else user.timezone,
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'utc_offset': now.strftime('%z'),
                'is_dst': now.dst().total_seconds() != 0 if now.dst() else False
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'current_timezone': user.timezone
            }, status=500)


class CountriesAPIView(APIView):
    """
    Comprehensive countries API using multiple data sources
    
    Data Sources:
    1. REST Countries API (primary) - Complete country data
    2. pycountry library (fallback) - Offline country data
    
    Features:
    - All 195+ countries worldwide
    - Multiple filter options
    - Search functionality
    - Caching for performance
    """
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.location_service = LocationService()
    
    @method_decorator(cache_page(60 * 60 * 12))  # Cache for 12 hours
    def get(self, request):
        """Get countries with filtering and search"""
        
        filter_type = request.query_params.get('filter', 'all')
        search = request.query_params.get('search', '')
        
        try:
            countries = self.location_service.get_all_countries(
                filter_type=filter_type,
                search=search
            )
            
            return Response({
                'success': True,
                'countries': countries,
                'total_count': len(countries),
                'filter_applied': filter_type,
                'search_query': search,
                'available_filters': ['all', 'popular', 'muslim_majority'],
                'data_source': 'REST Countries API + pycountry'
            })
            
        except Exception as e:
            logger.error(f"Error fetching countries: {e}")
            return Response({
                'success': False,
                'error': 'Failed to fetch countries',
                'message': 'Please try again later'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CitiesAPIView(APIView):
    """
    Comprehensive cities API using GeoNames database
    
    Data Source: GeoNames API (11M+ places worldwide)
    
    Features:
    - Cities, towns, villages for any country
    - Population data
    - Geographic coordinates
    - Administrative divisions
    - Search functionality
    - Caching for performance
    """
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.location_service = LocationService()
    
    @method_decorator(cache_page(60 * 60 * 6))  # Cache for 6 hours
    def get(self, request):
        """Get cities for a country with search and pagination"""
        
        country_code = request.query_params.get('country', '').upper()
        if not country_code:
            return Response({
                'success': False,
                'error': 'country parameter is required',
                'example': '/api/users/cities/?country=NG'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        search = request.query_params.get('search', '')
        limit = min(int(request.query_params.get('limit', 100)), 1000)
        
        try:
            cities = self.location_service.get_cities_for_country(
                country_code=country_code,
                search=search,
                limit=limit
            )
            
            return Response({
                'success': True,
                'country_code': country_code,
                'cities': cities,
                'total_count': len(cities),
                'search_query': search,
                'limit_applied': limit,
                'data_source': 'GeoNames API'
            })
            
        except Exception as e:
            logger.error(f"Error fetching cities for {country_code}: {e}")
            return Response({
                'success': False,
                'error': f'Failed to fetch cities for country: {country_code}',
                'message': 'Please check the country code and try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LocationAutocompleteAPIView(APIView):
    """
    Location autocomplete for signup forms
    
    Returns both countries and cities in a single response
    Optimized for frontend autocomplete components
    """
    permission_classes = [AllowAny]
    
    def __init__(self):
        super().__init__()
        self.location_service = LocationService()
    
    def get(self, request):
        """Autocomplete search for locations"""
        
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({
                'success': False,
                'error': 'Query must be at least 2 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        country_code = request.query_params.get('country', '')
        limit = min(int(request.query_params.get('limit', 10)), 50)
        
        try:
            results = []
            
            # Search countries if no specific country provided
            if not country_code:
                countries = self.location_service.get_all_countries(
                    filter_type='popular',
                    search=query
                )[:limit//2]
                
                for country in countries:
                    results.append({
                        'type': 'country',
                        'name': country['name'],
                        'code': country['code'],
                        'display': f"{country['name']} ({country['code']})",
                        'flag': country.get('flag', '')
                    })
            
            # Search cities
            if country_code:
                cities = self.location_service.get_cities_for_country(
                    country_code=country_code.upper(),
                    search=query,
                    limit=limit
                )
                
                for city in cities[:limit]:
                    results.append({
                        'type': 'city',
                        'name': city['name'],
                        'country_code': country_code.upper(),
                        'admin1': city.get('admin1', ''),
                        'display': f"{city['name']}, {city.get('admin1', country_code)}",
                        'population': city.get('population', 0),
                        'is_capital': city.get('is_capital', False)
                    })
            
            return Response({
                'success': True,
                'query': query,
                'results': results[:limit],
                'total_count': len(results)
            })
            
        except Exception as e:
            logger.error(f"Error in location autocomplete: {e}")
            return Response({
                'success': False,
                'error': 'Autocomplete search failed',
                'message': 'Please try again'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
