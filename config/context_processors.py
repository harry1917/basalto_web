from django.conf import settings

def cdn(request):
    return {
        "CDN_BASE_URL": getattr(settings, "CDN_BASE_URL", "").rstrip("/")
    }
