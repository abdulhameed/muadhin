import uuid
from rest_framework import viewsets, generics, permissions
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from .permissions import IsOwnerOrReadOnly
from .models import CustomUser, PasswordResetToken, UserPreferences, PrayerMethod, PrayerOffset, AuthToken
from .serializers import UserPreferencesSerializer, PrayerMethodSerializer, PrayerOffsetSerializer, CustomUserSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone


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

        # Generate and store a new reset token
        token = str(uuid.uuid4())
        # Delete any existing reset tokens for this user
        PasswordResetToken.objects.filter(user=user).delete()

        # Set expiry time - 24 hours from now
        expires_at = timezone.now() + timezone.timedelta(hours=24)

        # Create new token with expiry
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at,
            is_used=False,
            is_expired=False
        )

        # Send password reset email
        reset_link = request.build_absolute_uri(reverse('reset-password-confirm', args=[token]))
        send_mail(
            'Reset Your Password',
            f'Please click the following link to reset your password: {reset_link}\nThis link will expire in 24 hours.',
            settings.EMAIL_HOST_USER,
            [user.email],
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
            reset_token = PasswordResetToken.objects.get(token=token)

            # Check if token is already used
            if reset_token.is_used:
                return Response({'error': 'This reset link has already been used'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if token is expired
            current_time = timezone.now()
            if current_time > reset_token.expires_at or reset_token.is_expired:
                # Mark as expired
                reset_token.is_expired = True
                reset_token.save()
                return Response({'error': 'This reset link has expired'}, status=status.HTTP_400_BAD_REQUEST)

            user = reset_token.user

        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid reset link'}, status=status.HTTP_400_BAD_REQUEST)

        new_password = request.data.get('new_password')
        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        # Mark token as used instead of deleting
        reset_token.is_used = True
        reset_token.save()

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


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'email': user.email,
            # Include other user fields you need
        })
