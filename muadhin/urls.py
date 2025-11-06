"""
URL configuration for muadhin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.decorators import permission_classes, api_view
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.http import JsonResponse

def healthz(request):
    return JsonResponse({"status": "ok"})

router = DefaultRouter()

from rest_framework.authentication import SessionAuthentication

# Create schema view with explicit permissions
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

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.generic import View

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def swagger_ui_view(request):
    """
    Simple function-based view that returns a static Swagger UI page
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>Muadhin API Documentation</title>
        <style>
            body {
                font-family: sans-serif;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .info {
                background: #f4f4f4;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Muadhin API Documentation</h1>
            <div class="info">
                <p>This is a static page for API documentation. The API schema is available at:</p>
                <ul>
                    <li><a href="/swagger/?format=openapi">OpenAPI Schema</a></li>
                </ul>
                <p>Note: For the full interactive Swagger UI experience, you need to access this application from the browser directly.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def redoc_ui_view(request):
    """
    Simple function-based view that returns a static ReDoc UI page
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>Muadhin API Documentation (ReDoc)</title>
        <style>
            body {
                font-family: sans-serif;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .info {
                background: #f4f4f4;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Muadhin API Documentation (ReDoc)</h1>
            <div class="info">
                <p>This is a static page for API documentation. The API schema is available at:</p>
                <ul>
                    <li><a href="/swagger/?format=openapi">OpenAPI Schema</a></li>
                </ul>
                <p>Note: For the full interactive ReDoc experience, you need to access this application from the browser directly.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/swagger/', permanent=False), name='home'),
    path('api-view/', include(router.urls)),
    path('doc/', swagger_ui_view, name='schema-swagger-ui'),
    path('redoc/', redoc_ui_view, name='schema-redoc'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    path('api/', include('SalatTracker.urls')),
    path('api/', include('users.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/communications/', include('communications.urls')),
    # path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('healthz/', healthz),
]
