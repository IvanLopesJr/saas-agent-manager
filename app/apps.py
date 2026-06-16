from django.apps import AppConfig


class MultiEmpresasAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = 'Sistema Multi-Empresas'

    def ready(self):
        """Wire signals and ensure translation assets exist."""
        from . import signals  # noqa: F401
        try:
            from .utils.i18n import ensure_compiled_translations
        except Exception:
            return
        ensure_compiled_translations()
