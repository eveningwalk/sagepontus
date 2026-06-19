from django.conf import settings


def demo_flags(request):
    is_tester = (
        request.user.is_authenticated
        and request.user.groups.filter(name='tester').exists()
    )
    return {
        "DEMO_ENABLED": getattr(settings, "DEMO_ENABLED", False),
        "is_tester": is_tester,
    }
