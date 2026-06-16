"""Helpers for loading and applying SystemSettings."""

from urllib.parse import urljoin

from django.conf import settings

from ..models import SystemSettings


def apply_email_settings(settings_obj: SystemSettings):
    """Copy SMTP fields from SystemSettings to Django's runtime settings."""
    if settings_obj.smtp_host:
        settings.EMAIL_HOST = settings_obj.smtp_host
    if settings_obj.smtp_port:
        settings.EMAIL_PORT = settings_obj.smtp_port
    if settings_obj.smtp_user:
        settings.EMAIL_HOST_USER = settings_obj.smtp_user
        settings.DEFAULT_FROM_EMAIL = settings_obj.smtp_user
    smtp_password = settings_obj.get_smtp_password()
    if smtp_password:
        settings.EMAIL_HOST_PASSWORD = smtp_password
    # Always respect boolean truthiness for TLS (default True)
    settings.EMAIL_USE_TLS = True


def get_system_settings(*, apply_email: bool = False) -> SystemSettings:
    """
    Return the singleton SystemSettings instance.

    Optionally mirror SMTP fields into django.conf.settings.
    """
    settings_obj = SystemSettings.get_settings()

    if apply_email:
        apply_email_settings(settings_obj)

    return settings_obj


def build_system_absolute_uri(path: str, *, request=None) -> str:
    """
    Build an absolute URL using the configured domain when enabled.

    Falls back to request.build_absolute_uri when available.
    """
    system_settings = get_system_settings()
    if system_settings.use_custom_domain and system_settings.custom_domain:
        base = system_settings.custom_domain.rstrip('/') + '/'
        # urljoin handles both absolute and relative paths
        return urljoin(base, path.lstrip('/'))

    if request is not None:
        # path might already be absolute (e.g., password reset links)
        if path.startswith(('http://', 'https://')):
            return path
        return request.build_absolute_uri(path)

    raise ValueError("Não é possível construir a URL absoluta sem request ou domínio configurado.")
