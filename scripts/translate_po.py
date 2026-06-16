# -*- coding: utf-8 -*-
from pathlib import Path
import polib
from deep_translator import GoogleTranslator

BASE = Path(r"app/locale")
pt_po = BASE / "pt_BR" / "LC_MESSAGES" / "django.po"
po = polib.pofile(str(pt_po))

def build_translation(dest, language_team):
    translator = GoogleTranslator(source='pt', target=dest)
    target_po = polib.POFile()
    target_po.metadata = {
        'Project-Id-Version': po.metadata.get('Project-Id-Version', ''),
        'Report-Msgid-Bugs-To': po.metadata.get('Report-Msgid-Bugs-To', ''),
        'POT-Creation-Date': po.metadata.get('POT-Creation-Date', ''),
        'PO-Revision-Date': po.metadata.get('PO-Revision-Date', ''),
        'Last-Translator': language_team,
        'Language-Team': language_team,
        'Language': dest,
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
        'Plural-Forms': 'nplurals=2; plural=(n != 1);'
    }

    entries = list(po)
    translations_map = {}
    batch = []
    keys = []

    for idx, entry in enumerate(entries):
        if entry.msgid == '':
            translations_map[idx] = ''
            continue
        batch.append(entry.msgid)
        keys.append(idx)
        if len(batch) == 50:
            translated = translator.translate_batch(batch)
            for key, value in zip(keys, translated):
                translations_map[key] = value
            batch.clear()
            keys.clear()

    if batch:
        translated = translator.translate_batch(batch)
        for key, value in zip(keys, translated):
            translations_map[key] = value

    for idx, entry in enumerate(entries):
        new_entry = polib.POEntry(msgid=entry.msgid)
        if entry.msgid == '':
            new_entry.msgstr = ''
        else:
            new_entry.msgstr = translations_map.get(idx, entry.msgid)
        new_entry.occurrences = entry.occurrences
        new_entry.comment = entry.comment
        new_entry.tcomment = entry.tcomment
        target_po.append(new_entry)

    dest_dir = BASE / dest / 'LC_MESSAGES'
    dest_dir.mkdir(parents=True, exist_ok=True)
    target_po.save(str(dest_dir / 'django.po'))

build_translation('en', 'English Team')
build_translation('es', 'Spanish Team')
