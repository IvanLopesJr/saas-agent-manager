import ast
import re
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path('.').resolve()

alpha_re = re.compile(r'[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF]')


def normalize(text):
    return re.sub(r'\s+', ' ', text.strip())


def looks_user_facing(text):
    norm = normalize(text)
    if not norm:
        return False
    if not alpha_re.search(norm):
        return False
    if norm.lower().startswith('http'):
        return False
    if re.fullmatch(r'[0-9]+', norm):
        return False
    if re.fullmatch(r'[A-Z0-9_]+', norm):
        return False
    if re.fullmatch(r'[a-z0-9_]+', norm):
        return False
    if re.fullmatch(r'[a-z0-9_-]+', norm):
        return False
    if norm.startswith('.') and ' ' not in norm:
        return False
    if norm.startswith('/') and ' ' not in norm:
        return False
    if '/' in norm and ' ' not in norm:
        return False
    if norm.startswith('#') and re.fullmatch(r'#[0-9A-Fa-f]{3,8}', norm):
        return False
    if len(norm) <= 1:
        return False
    return True


def load_po_strings():
    po_strings = set()
    for po_path in ROOT.glob('app/locale/*/LC_MESSAGES/django.po'):
        try:
            content = po_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for match in re.finditer(r'^msgid\s+"((?:[^"\\]|\\.)*)"', content, re.MULTILINE):
            text = match.group(1)
            text = text.encode('utf-8', 'replace').decode('unicode_escape')
            po_strings.add(normalize(text))
    return po_strings


PO_STRINGS = load_po_strings()


def add_result(results, path, line, text, kind):
    norm = normalize(text)
    if not norm:
        return
    if norm in PO_STRINGS:
        return
    results.append({'path': str(path.relative_to(ROOT)), 'line': line, 'text': text.strip(), 'kind': kind})


class TemplateTextCollector(HTMLParser):
    def __init__(self, path, results):
        super().__init__()
        self.path = path
        self.results = results

    def handle_data(self, data):
        if '{' in data:
            return
        text = data.strip()
        if not text or not looks_user_facing(text):
            return
        line, _ = self.getpos()
        add_result(self.results, self.path, line, text, 'template_text')


TEMPLATE_ATTRS = [
    'placeholder', 'title', 'alt', 'aria-label', 'aria-labelledby', 'aria-describedby',
    'aria-description', 'aria-live', 'aria-placeholder', 'data-title', 'data-tooltip',
    'data-confirm', 'data-message', 'data-help', 'data-bs-original-title', 'value'
]
ATTR_PATTERN = re.compile(
    r'(' + '|'.join(TEMPLATE_ATTRS) + r')\s*=\s*("([^"]*)"|\'([^\']*)\')',
    re.IGNORECASE
)


def scan_template(path, results):
    content = path.read_text(encoding='utf-8')
    collector = TemplateTextCollector(path, results)
    collector.feed(content)
    for idx, line in enumerate(content.splitlines(), start=1):
        for match in ATTR_PATTERN.finditer(line):
            value = match.group(3) if match.group(3) is not None else match.group(4)
            if not value or '{' in value:
                continue
            if not looks_user_facing(value):
                continue
            add_result(results, path, idx, value, 'template_attr')


LOCALIZATION_FUNCS = {
    '_', 'gettext', 'gettext_lazy', 'ugettext', 'ugettext_lazy', 'pgettext', 'ngettext',
    'pgettext_lazy', 'npgettext', 'ngettext_lazy'
}


def is_localized(node, stack):
    for parent in reversed(stack[:-1]):
        if isinstance(parent, ast.Call):
            func = parent.func
            if isinstance(func, ast.Name) and func.id in LOCALIZATION_FUNCS:
                return True
            if isinstance(func, ast.Attribute) and func.attr in LOCALIZATION_FUNCS:
                return True
    return False


def collect_docstring_ids(node, store):
    if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        body = getattr(node, 'body', None)
        if body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                store.add(id(first.value))
        for child in getattr(node, 'body', []):
            collect_docstring_ids(child, store)
    else:
        for child in ast.iter_child_nodes(node):
            collect_docstring_ids(child, store)


def scan_python(path, results):
    rel = str(path).replace('\\', '/')
    if '/management/commands/' in rel or rel.endswith('/apps.py'):
        return
    try:
        source = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    stack = []
    docstring_ids = set()
    collect_docstring_ids(tree, docstring_ids)

    class Visitor(ast.NodeVisitor):
        def visit(self, node):
            stack.append(node)
            result = super().visit(node)
            stack.pop()
            return result

        def visit_Constant(self, node):
            if not isinstance(node.value, str):
                return
            if id(node) in docstring_ids:
                return
            if len(stack) >= 2 and isinstance(stack[-2], ast.Expr):
                container = stack[-3] if len(stack) >= 3 else None
                if isinstance(container, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    return
                return
            if is_localized(node, stack):
                return
            if looks_user_facing(node.value):
                add_result(results, path, getattr(node, 'lineno', 0), node.value, 'python_string')

        def visit_JoinedStr(self, node):
            if is_localized(node, stack):
                return
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                else:
                    parts.append('{expr}')
            text = ''.join(parts)
            if looks_user_facing(text):
                add_result(results, path, getattr(node, 'lineno', 0), text, 'python_fstring')
            self.generic_visit(node)

    Visitor().visit(tree)


JS_STRING = re.compile(r'("([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\')')


def scan_js(path, results):
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return
    for idx, line in enumerate(content.splitlines(), start=1):
        for match in JS_STRING.finditer(line):
            value = match.group(0)[1:-1]
            if not looks_user_facing(value):
                continue
            add_result(results, path, idx, value, 'js_string')


def main():
    results = []
    for template in (ROOT / 'app' / 'templates').rglob('*.html'):
        scan_template(template, results)
    for py_file in ROOT.rglob('*.py'):
        if '\\migrations\\' in str(py_file) or '/migrations/' in str(py_file).replace('\\', '/'):
            continue
        scan_python(py_file, results)
    for js_file in (ROOT / 'app' / 'static' / 'js').rglob('*.js'):
        scan_js(js_file, results)
    results.sort(key=lambda item: (item['path'], item['line']))
    for item in results:
        print(f"{item['path']}:{item['line']}|{item['kind']}|{item['text']}")


if __name__ == '__main__':
    main()
