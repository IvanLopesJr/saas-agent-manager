"""Context processors used across templates."""

from django.conf import settings

from .utils.system_settings import get_system_settings


def system_settings(request):
    """
    Inject current SystemSettings instance into every template.
    """
    settings_obj = get_system_settings()

    return {"system_settings": settings_obj}
