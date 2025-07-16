import uuid
from rest_framework import viewsets, generics, permissions
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse

from subscriptions.services.subscription_service import SubscriptionService
from .permissions import IsOwnerOrReadOnly
from .models import CustomUser, UserPreferences, PrayerMethod, PrayerOffset, AuthToken
from .serializers import UserPreferencesSerializer, PrayerMethodSerializer, PrayerOffsetSerializer, CustomUserSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.conf import settings
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes, permission_classes
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.decorators import action

# from django.contrib.auth.models import User


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


