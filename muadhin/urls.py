"""
URL configuration for muadhin project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


# Health check endpoint
def healthz(request):
    return JsonResponse({"status": "ok"})


# Swagger/ReDoc schema configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Personal Muadhin API",
        default_version='v1',
        description="API for Personal Muadhin",
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="Your License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)


# Main router for DRF API root
router = DefaultRouter()


urlpatterns = [
    # Root - Redirect to DRF API root
    path('', RedirectView.as_view(url='/api/', permanent=False), name='home'),

    # Admin
    path('admin/', admin.site.urls),

    # API endpoints
    path('api/', include(router.urls)),  # DRF API root
    path('api/', include('SalatTracker.urls')),
    path('api/', include('users.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/communications/', include('communications.urls')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc-ui'),

    # Health check
    path('healthz/', healthz, name='healthz'),
]
