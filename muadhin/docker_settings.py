"""
Docker-specific settings for the muadhin project.
This file is loaded by the Docker environment to override specific settings.
"""
from .settings import *

# Override REST_FRAMEWORK settings to allow Swagger UI access while keeping permission classes
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = (
    'rest_framework.permissions.AllowAny',  # Allow public access to Swagger
)
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
    'rest_framework_simplejwt.authentication.JWTAuthentication',
)
REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'rest_framework.schemas.coreapi.AutoSchema'

# Disable authentication for Swagger UI
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        },
    },
    'USE_SESSION_AUTH': False,
    'VALIDATOR_URL': None,
    'DOC_EXPANSION': 'list',
}

# Static files configuration for Docker
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'  # Use standard storage instead of WhiteNoise

# Allow all origins for Docker development
CORS_ALLOW_ALL_ORIGINS = True

# Allow localhost for development
ALLOWED_HOSTS = ['*']