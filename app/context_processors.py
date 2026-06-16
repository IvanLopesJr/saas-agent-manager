"""Context processors used across templates."""

from django.conf import settings

from .utils.system_settings import get_system_settings


def system_settings(request):
    """
    Inject current SystemSettings instance into every template.

    Also ensures SMTP-related Django settings reflect the latest values.
    """
    settings_obj = get_system_settings(apply_email=True)

    # Ensure DEFAULT_FROM_EMAIL always has a sensible fallback
    if not getattr(settings, "DEFAULT_FROM_EMAIL", None):
        settings.DEFAULT_FROM_EMAIL = settings_obj.smtp_user or ""

    return {"system_settings": settings_obj}
