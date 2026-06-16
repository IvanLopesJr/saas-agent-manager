from pathlib import Path
from collections import Counter

po_path = Path('app/locale/en/LC_MESSAGES/django.po')
text = po_path.read_text(encoding='utf-8')
entries = []
msgid = None
block = []
for line in text.splitlines():
    if line.startswith('msgid '):
        if msgid is not None:
            entries.append((msgid, '\n'.join(block)))
        block = [line]
        msgid = line[6:]
    else:
        block.append(line)
if msgid is not None:
    entries.append((msgid, '\n'.join(block)))

counter = Counter(mid for mid,_ in entries if mid != '\"\"')
dups = [mid for mid,count in counter.items() if count > 1]
print('duplicate count', len(dups))
for mid in dups[:10]:
    print(mid)
