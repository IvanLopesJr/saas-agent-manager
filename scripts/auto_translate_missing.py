import polib
from deep_translator import GoogleTranslator
from pathlib import Path

BASE = Path('app/locale')
pt_po = polib.pofile(str(BASE / 'pt_BR' / 'LC_MESSAGES' / 'django.po'))

SKIP_PATTERNS = ['%( ', '%(', '{', '}']

def needs_skip(text):
    return any(pat in text for pat in SKIP_PATTERNS)

for lang, target_code in [('en', 'en'), ('es', 'es')]:
    po_path = BASE / lang / 'LC_MESSAGES' / 'django.po'
    po = polib.pofile(str(po_path))
    translator = GoogleTranslator(source='pt', target=target_code)
    updated = False
    for entry in po:
        if not entry.msgid:
            continue
        if entry.msgstr:
            continue
        source_entry = pt_po.find(entry.msgid)
        source_text = source_entry.msgstr if source_entry and source_entry.msgstr else entry.msgid
        if needs_skip(source_text) or needs_skip(entry.msgid):
            entry.msgstr = source_text
            updated = True
            continue
        try:
            translation = translator.translate(source_text)
        except Exception:
            translation = source_text
        entry.msgstr = translation
        updated = True
    if updated:
        po.save(str(po_path))
