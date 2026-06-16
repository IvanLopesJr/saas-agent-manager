import polib
for lang in ['en', 'es']:
    po = polib.pofile(f'app/locale/{lang}/LC_MESSAGES/django.po')
    fuzzy = [e for e in po if e.fuzzy]
    print(f'{lang}: {len(fuzzy)} fuzzy entries')
    for e in fuzzy[:30]:
        print('-', e.msgid, '=>', e.msgstr)
    print()
