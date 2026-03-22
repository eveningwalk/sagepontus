from django.conf import settings


def demo_flags(_request):
    return {
        "DEMO_ENABLED": getattr(settings, "DEMO_ENABLED", False),
    }
