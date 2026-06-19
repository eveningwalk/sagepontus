from django.conf import settings


def feature_flags(request):
    return {"FEATURES": settings.FEATURES}
