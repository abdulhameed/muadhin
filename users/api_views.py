import uuid
from rest_framework import viewsets, generics, permissions
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from .permissions import IsOwnerOrReadOnly
from .models import CustomUser, UserPreferences, PrayerMethod, PrayerOffset, AuthToken
from .serializers import UserPreferencesSerializer, PrayerMethodSerializer, PrayerOffsetSerializer, CustomUserSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes, permission_classes
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

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
    queryset = UserPreferences.objects.all()
    serializer_class = UserPreferencesSerializer


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
