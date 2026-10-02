"""Resolve snapshot labels and keep tutorial navigation focused on main sections."""
import json
from pathlib import Path


def on_page_markdown(markdown, **kwargs):
    snapshot = json.loads((Path(__file__).parent/'docs/assets/build-manifest.json').read_text())
    for name in ('source_version', 'python_requires', 'api_modules', 'functions_and_classes', 'class_members', 'citation_date', 'notebooks', 'saved_figures'):
        markdown = markdown.replace('{{ ' + name + ' }}', str(snapshot[name]))
    dependency_rows = ['| Install target | Declared Python requirements |', '|---|---|']
    for name, requirements in [('Core', snapshot['dependencies']), *snapshot['optional_dependencies'].items()]:
        dependency_rows.append('| ' + name + ' | ' + ', '.join('`'+item+'`' for item in requirements) + ' |')
    markdown = markdown.replace('{{ dependency_table }}', '\n'.join(dependency_rows))
    return markdown


def on_page_content(html, page, **kwargs):
    """Prune only the tutorial sidebar; retain all body headings and anchors."""
    if not page.file.src_uri.startswith('tutorials/'):
        return html

    notebook = '../assets/notebooks/' in (page.markdown or '')
    # Notebook headings are shifted down one level during conversion. H4
    # contains API signatures and cell-level explanations, rather than steps.
    max_level = 3 if notebook else 2

    def main_sections(items):
        kept = []
        for item in items:
            if item.level <= max_level:
                item.children = main_sections(item.children)
                kept.append(item)
        return kept

    page.toc.items = main_sections(page.toc.items)
    if notebook and page.toc.items:
        title = page.toc.items[0]
        sections = title.children if title.level == 1 else page.toc.items
        if sections:
            overview = sections[0]
            overview.title = 'Overview'
            # Most notebooks place every step under one introductory heading.
            # Lift those steps so the sidebar does not indent the entire guide.
            if len(sections) == 1:
                steps = overview.children
                overview.children = []
                for step in steps:
                    step.level = overview.level
                sections.extend(steps)
    return html
