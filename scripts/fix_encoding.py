from pathlib import Path
from ftfy import fix_text
exts={'.py','.html','.txt','.md','.po','.js','.css','.json'}
changed=[]
for path in Path('.').rglob('*'):
    if path.suffix.lower() not in exts or not path.is_file():
        continue
    try:
        text=path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    fixed=fix_text(text)
    if fixed!=text:
        path.write_text(fixed, encoding='utf-8')
        changed.append(str(path))
print('Fixed', len(changed), 'files')
