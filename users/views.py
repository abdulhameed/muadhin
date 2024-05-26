from rest_framework import viewsets, permissions
from .models import CustomUser, UserPreferences, PrayerMethod, PrayerOffset
from .serializers import UserPreferencesSerializer, PrayerMethodSerializer, PrayerOffsetSerializer, CustomUserSerializer, PrayerMethodGenSerializer
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsOwnerOrReadOnly


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
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    # def get_permissions(self):
    #     """
    #     Instantiates and returns the list of permissions that this view requires.
    #     """
    #     if self.action in ['update', 'partial_update', 'destroy']:
    #         permission_classes = [permissions.IsAuthenticated]
    #     else:
    #         permission_classes = [permissions.AllowAny]
    #     return [permission() for permission in permission_classes]


class PrayerMethodGenSerializer(viewsets.ModelViewSet):
    queryset = PrayerMethod.objects.all()
    serializer_class = PrayerMethodGenSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    # def get_permissions(self):
    #     """
    #     Instantiates and returns the list of permissions that this view requires.
    #     """
    #     if self.action in ['update', 'partial_update', 'destroy']:
    #         permission_classes = [permissions.IsAuthenticated]
    #     else:
    #         permission_classes = [permissions.AllowAny]
    #     return [permission() for permission in permission_classes]

class PrayerOffsetViewSet(viewsets.ModelViewSet):
    queryset = PrayerOffset.objects.all()
    serializer_class = PrayerOffsetSerializer
