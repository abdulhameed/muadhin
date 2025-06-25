# decorators/subscription_required.py
from functools import wraps
from rest_framework.response import Response


def feature_required(feature_name):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_feature(feature_name):
                return Response({
                    'error': 'Feature not available in your current plan',
                    'required_feature': feature_name,
                    'upgrade_url': '/api/subscriptions/'
                }, status=403)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage in views:
@feature_required('adhan_call_audio')
def schedule_audio_adhan_call(request):
    # Only accessible to Premium users
    pass
