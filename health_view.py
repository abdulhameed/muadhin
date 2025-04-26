from django.http import HttpResponse

def ping(request):
    """
    Absolutely minimal health check that just returns a 200 OK response
    """
    return HttpResponse("OK")
