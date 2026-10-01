"""Check local HTML targets, fragments, asset paths, API coverage, and source hashes."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT/'site'

class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ('href', 'src', 'data-snapshot'):
            if key in attrs:
                self.links.append(attrs[key])

def main():
    pages = {p.resolve(): Page(p) for p in SITE.rglob('*.html') if not p.name.startswith('._')}
    errors = []
    if not pages:
        errors.append('No built HTML found; run python manage.py build first.')
    checked = 0
    for path, page in pages.items():
        if any('{{ ' + name + ' }}' in path.read_text(encoding='utf-8') for name in ('source_version', 'python_requires', 'api_modules', 'functions_and_classes', 'notebooks', 'saved_figures')):
            errors.append(f'Unresolved snapshot label: {path.relative_to(SITE)}')
        # Material's standalone 404 template intentionally has deployment-root-relative links.
        if path.name == '404.html':
            continue
        for href in page.links:
            url = urlsplit(href)
            if url.scheme or url.netloc or not href:
                continue
            target = ((SITE/unquote(url.path).lstrip('/')) if url.path.startswith('/') else
                      path.parent/unquote(url.path)) if url.path else path
            if target.is_dir():
                target = target/'index.html'
            target = target.resolve()
            checked += 1
            if not target.exists():
                errors.append(f'{path.relative_to(SITE)}: missing target {href}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(SITE)}: missing fragment {href}')
    inventory = json.loads((ROOT/'docs/assets/api-inventory.json').read_text())
    for record in inventory:
        target = (SITE/'api'/record['module'].replace('.', '-')/'index.html').resolve()
        if target not in pages or record['name'] not in pages[target].ids:
            errors.append(f'API definition not rendered: {record["name"]}')
    manifest = json.loads((ROOT/'docs/assets/build-manifest.json').read_text())
    current_sources = {str(p.relative_to(ROOT.parent)) for p in (ROOT.parent/'hyperproc').rglob('*.py') if not p.name.startswith('._')}
    if current_sources != set(manifest['package_source_sha256']):
        errors.append('Package module inventory changed since generation')
    for name, expected in (manifest['package_source_sha256'] | manifest['metadata_source_sha256'] | manifest.get('map_recordings_sha256', {})).items():
        if hashlib.sha256((ROOT.parent/name).read_bytes()).hexdigest() != expected:
            errors.append(f'Package source changed since generation: {name}')
    for name in ('LICENSE', 'CITATION.cff'):
        if (SITE/'assets'/name).read_bytes() != (ROOT.parent/name).read_bytes():
            errors.append(f'Project metadata copy mismatch: {name}')
    notebooks = json.loads((ROOT/'docs/assets/notebook-inventory.json').read_text())
    for record in notebooks:
        original = ROOT.parent/'tests/0_src_code'/record['file']
        copy = SITE/'assets/notebooks'/record['file']
        if any(hashlib.sha256(p.read_bytes()).hexdigest() != record['sha256'] for p in (original, copy)):
            errors.append(f'Notebook copy/source mismatch: {record["file"]}')
    if errors:
        print('\n'.join(sorted(set(errors))))
        sys.exit(1)
    print(f'PASS: {len(pages)} HTML pages; {checked} local links/assets/fragments; '
          f'{len(inventory)} API definitions; {len(notebooks)} unchanged notebook copies; package source hashes match.')

if __name__ == '__main__':
    main()
