"""
Utilities to keep translation files compiled even when GNU gettext tools
aren't available in the environment (e.g., Windows containers).
"""

from pathlib import Path
from threading import Lock

from django.conf import settings

try:
    import polib
except ImportError:  # pragma: no cover
    polib = None

_compiled = False
_lock = Lock()


def compile_locale_files(force=False):
    """Compile every django.po under app/locale into its corresponding .mo."""
    if polib is None:
        return []

    locale_dir = Path(settings.BASE_DIR) / 'app' / 'locale'
    if not locale_dir.exists():
        return []

    compiled = []
    for po_path in locale_dir.rglob('django.po'):
        mo_path = po_path.with_suffix('.mo')
        needs_compile = force or not mo_path.exists() or po_path.stat().st_mtime > mo_path.stat().st_mtime
        if needs_compile:
            po = polib.pofile(str(po_path))
            mo_path.parent.mkdir(parents=True, exist_ok=True)
            po.save_as_mofile(str(mo_path))
            compiled.append((po_path, mo_path))

    return compiled


def ensure_compiled_translations():
    """Lazy compilation guard used during app start."""
    global _compiled
    if _compiled:
        return

    with _lock:
        if _compiled:
            return
        compile_locale_files()
        _compiled = True
