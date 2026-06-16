"""
Update .po files: replace chatbot/chatbots in msgstr only.
Usage: python rename_chatbot_po.py
"""

import re

LANGUAGES = {
    'pt_BR': {'Chatbot': 'Agente', 'Chatbots': 'Agentes', 'chatbot': 'agente', 'chatbots': 'agentes'},
    'en':     {'Chatbot': 'Agent',  'Chatbots': 'Agents',  'chatbot': 'agent',  'chatbots': 'agents'},
    'es':     {'Chatbot': 'Agente', 'Chatbots': 'Agentes', 'chatbot': 'agente', 'chatbots': 'agentes'},
}

for lang, replacements in LANGUAGES.items():
    path = f'app/locale/{lang}/LC_MESSAGES/django.po'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = []
    in_msgstr = False

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('msgid '):
            in_msgstr = False
        elif stripped.startswith('msgstr '):
            in_msgstr = True

        if in_msgstr:
            for old, new in sorted(replacements.items(), key=lambda x: -len(x[0])):
                line = line.replace(old, new)

        new_lines.append(line)

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

    print(f'Updated {path}')
