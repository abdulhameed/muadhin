from django.http import JsonResponse
from django.db import connection


def health_check(request):
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            one = cursor.fetchone()[0]
            if one != 1:
                return JsonResponse(
                    {"status": "error", "message": "Database check failed"},
                    status=500
                )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "healthy"})


def simple_health_check(request):
    # A very basic health check that doesn't depend on database
    return JsonResponse({"status": "healthy"})
