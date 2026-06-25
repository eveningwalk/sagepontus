from django.contrib.auth.models import User


def track(user: User, event: str, **meta) -> None:
    """Fire-and-forget event log. Never raises — tracking must never break the main flow."""
    try:
        from vertical_pt.models import UserEvent
        UserEvent.objects.create(user=user, event=event, meta=meta)
    except Exception:
        pass
