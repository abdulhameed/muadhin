from django.http import JsonResponse

def ping(request):
    """
    A simple health check that doesn't depend on the database
    """
    return JsonResponse({"status": "ok"})
