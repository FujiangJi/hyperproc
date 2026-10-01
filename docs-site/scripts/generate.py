"""Generate reference, sensor guides, and notebook snapshots without importing hyperproc.

Only writes under docs-site. Notebook source and package source are read-only inputs.
"""
from __future__ import annotations
import ast
import base64
import hashlib
import json
import re
import shutil
import tomllib
from notebook_maps import map_snapshot, WIDGET_VIEW
from granule_recordings import result_context, recorded_snapshot
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DOCS = ROOT / 'docs'
PKG = REPO / 'hyperproc'


def write(path, value):
    target = DOCS / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding='utf-8')


def module_of(path):
    parts = list(path.relative_to(REPO).with_suffix('').parts)
    if parts[-1] == '__init__': parts.pop()
    return '.'.join(parts)


def page_of(module):
    return 'api/' + module.replace('.', '-') + '.md'


def generate_api():
    trees = {module_of(p): (p, ast.parse(p.read_text())) for p in sorted(PKG.rglob('*.py')) if not p.name.startswith('._')}
    aliases = {}
    exports = {}
    definitions = {}
    records = []
    groups = {'Core': [], 'Archive': [], 'Readers': [], 'Corrections': [], 'Spectral': [], 'Atmosphere': []}
    for module, (p, tree) in trees.items():
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    aliases[module+'.'+(alias.asname or alias.name)] = node.module+'.'+alias.name
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                definitions[module+'.'+node.name] = module
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id == '__all__':
                            try: exports[module] = ast.literal_eval(node.value)
                            except (ValueError, TypeError): pass
                        elif isinstance(node.value, ast.Name): aliases[module+'.'+target.id] = module+'.'+node.value.id
                        definitions[module+'.'+target.id] = module
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                definitions[module+'.'+node.target.id] = module

    # Lazy optional exports are not top-level imports. Link them when static
    # inspection finds one unambiguous definition in this module's descendants.
    for module, names in exports.items():
        if module+'.__getattr__' not in definitions:
            continue
        for name in names:
            qualified = module+'.'+name
            candidates = [key for key in definitions if key.startswith(module+'.')
                          and key.endswith('.'+name) and key != qualified]
            if qualified not in aliases and qualified not in definitions and len(candidates) == 1:
                aliases[qualified] = candidates[0]

    def resolve(name):
        seen = set()
        while name in aliases and name not in seen:
            seen.add(name); name = aliases[name]
        return name

    for module, (p, tree) in trees.items():
        members = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        members += [n.target.id for n in tree.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id.isupper()]
        members += [t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name) and t.id.isupper()]
        members += [name for name in exports.get(module, []) if resolve(module+'.'+name) == module+'.'+name and module+'.'+name in definitions]
        members = list(dict.fromkeys(members))
        group = ('Archive' if module.startswith('hyperproc.archive') else
                 'Atmosphere' if module.startswith('hyperproc.atmos') else
                 'Readers' if '.readers' in module else 'Corrections' if '.correct' in module else
                 'Spectral' if '.spectral' in module else 'Core')
        path = page_of(module)
        groups[group].append({module: path})
        header = f'# `{module}`\n\n<span class="status-pill">Source-derived reference</span>\n\n'
        header += f'Implementation: `{p.relative_to(REPO)}`. Signatures, defaults, docstrings, and expandable source are extracted statically; the module is not imported or executed. Names beginning with `_` are implementation details, not a stable public API.\n\n'
        header += 'Use the function signature as the authority for individual parameter defaults and return annotations. Original docstrings sometimes group parameter names or wrap return descriptions across lines; these descriptions are preserved rather than inferred or rewritten.\n\n'
        if module in exports:
            header += '## Exported entry points\n\n| Importable name | Definition |\n|---|---|\n'
            for name in exports[module]:
                target = resolve(module+'.'+name)
                owner = definitions.get(target)
                if owner:
                    link = Path(page_of(owner)).name+'#'+target
                    header += f'| `{module}.{name}` | [`{target}`]({link}) |\n'
                elif target in trees:
                    header += f'| `{module}.{name}` | [Module]({Path(page_of(target)).name}) |\n'
                else:
                    header += f'| `{module}.{name}` | Exported constant/module; see source below |\n'
            header += '\n'
        if module in ('hyperproc.correct', 'hyperproc.correct.cfactor', 'hyperproc.atmos', 'hyperproc.readers._common'):
            header += '!!! warning "Docstring evidence boundary"\n    Original docstrings may contain historical validation claims or simplified scientific explanations. Their presence is not independent verification. Consult the maintained workflow guides and validation page before reusing such claims.\n\n'
        options = {'members': members, 'show_root_heading': False, 'show_root_toc_entry': False,
                   'show_if_no_docstring': True, 'filters': [], 'members_order': 'source'}
        header += f'::: {module}\n' + '    options:\n' + '\n'.join('      '+x for x in yaml.safe_dump(options,sort_keys=False).splitlines())+'\n'
        write(path, header)
        for n in tree.body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                records.append({'name':module+'.'+n.name,'module':module,'line':n.lineno,
                                'kind':'class' if isinstance(n,ast.ClassDef) else 'function',
                                'documented':bool(ast.get_docstring(n)), 'private':n.name.startswith('_')})
    index = '# API reference\n\nThe reference covers every local Python module, including public interfaces, lower-level functions, classes, and implementation helpers. Prefer documented package exports for application code. **Source-derived does not mean scientifically validated.**\n\n'
    index += '## Where to begin\n\n| Task | Main namespace |\n|---|---|\n'
    for desc,module in [('Open, inspect, export, mask, or analyze','hyperproc'),('Find granules, check credentials, download, or draw a search map','hyperproc.archive'),('Airborne topographic/FlexBRDF or satellite NBAR','hyperproc.correct'),('Atmospheric retrieval orchestration','hyperproc.atmos'),('Spectral transforms and resampling','hyperproc.spectral')]:
        index += f'| {desc} | [`{module}`]({Path(page_of(module)).name}) |\n'
    index += '\n## Module index\n\n'
    for group, entries in groups.items():
        index += f'### {group}\n\n'+'\n'.join(f'- [`{m}`]({Path(v).name})' for entry in entries for m,v in entry.items())+'\n\n'
    index += '## Documentation gaps\n\nFunctions with no docstring are still listed with their signature and source. Their prose explanation is **under construction**; parameter meaning is not invented. Imported third-party APIs are not duplicated here.\n'
    write('api/index.md',index)
    write('assets/api-inventory.json',json.dumps(records,indent=2))
    return groups, records


def generate_notebooks():
    records=[]
    for src in sorted((REPO/'tests/0_src_code').glob('*.ipynb')):
        if src.name.startswith('._'): continue
        nb=json.loads(src.read_text())
        slug=src.stem.replace('_','-')
        title=src.stem.replace('_window_tutorial',' — window tutorial').replace('_tutorial',' — tutorial')
        names={'search_download':'Archive search and download','aviris3':'AVIRIS-3','aviris5':'AVIRIS-5','avirisng':'AVIRIS-NG','avirisclassic':'AVIRIS Classic',
               'neon':'NEON AOP','emit':'EMIT','prisma':'PRISMA','pace':'PACE OCI','enmap':'EnMAP','desis':'DESIS','tanager':'Tanager'}
        for key,val in names.items():
            if title.startswith(key): title=title.replace(key,val,1); break
        outputs=sum(len(c.get('outputs',[])) for c in nb['cells'])
        errors=sum(o.get('output_type')=='error' for c in nb['cells'] for o in c.get('outputs',[]))
        state='Saved outputs available — not rerun' if outputs else 'No saved outputs — execution unverified'
        record={'title':title,'file':src.name,'page':'tutorials/'+slug+'.md','cells':len(nb['cells']),
                'outputs':outputs,'errors':errors,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
        records.append(record)
        out=[f'# {title}\n\n<span class="status-pill">{state}</span>\n\n',
             f'[Download the original notebook](../assets/notebooks/{src.name}) · Source: `tests/0_src_code/{src.name}`\n\n',
             '!!! warning "Archived tutorial, not an automatic test"\n    This is a read-only rendering of the existing notebook. Code was not executed for the website. Paths and saved outputs belong to the original environment. Some prose describes intent rather than the exact current implementation. Read the [notebook caveats](caveats.md) before running cells. Cells can write large files, download external data, or reuse cached results.\n\n',
             '!!! note "How to read outputs"\n    Figures below are stored notebook outputs, not newly generated results. Text outputs are expanded by default and can be collapsed; long logs may be shortened for readability; the downloadable notebook retains the complete original output.\n\n']
        if src.stem.startswith('aviris') or src.stem.startswith('neon'):
            out += ['!!! warning "Airborne tutorial defaults"\n    Inspect `SAMPLE_REGION`, `SAMPLE_ROWS`, and `force_topo` before use. Row-subset fitting is not full-flightline fitting. Forced correction is a demonstration, not a recommendation. Satellite topographic effects are not universally absent; that claim in historical prose is not a general scientific rule.\n\n']
        figure_count=0
        map_count=0
        for i,cell in enumerate(nb['cells']):
            s=''.join(cell.get('source',[]))
            if not s.strip(): continue
            if cell['cell_type']=='markdown':
                # Place the original notebook's heading hierarchy below this page title.
                s=re.sub(r'^(#{1,5}) ',r'\1# ',s,flags=re.M)
                out += [s+'\n\n']
            elif cell['cell_type']=='code':
                out += [f'<div class="nb-cell-label">Source cell {i+1} · saved execution {cell.get("execution_count") or "not recorded"}</div>\n\n',f'```python\n{s}\n```\n\n']
                for j,o in enumerate(cell.get('outputs',[])):
                    data=o.get('data',{})
                    if WIDGET_VIEW in data and 'search_map(' in s:
                        snapshot = map_snapshot(nb, data)
                        if snapshot is not None:
                            snapshot = recorded_snapshot(ROOT/'map-recordings'/src.stem, result_context(nb, i), snapshot)
                            rel = f'assets/notebook-maps/{slug}/cell-{i+1}-{j}.json'
                            write(rel, json.dumps(snapshot, indent=2))
                            if snapshot['evidence'] == 'matched-granule-metadata':
                                count = len(snapshot['layers'])
                                caption = f'{count} granules from the saved search results. Hover or click an outline to inspect it; use the granule list for overlapping scenes.'
                                if any(layer['granule']['sensor'] == 'NEON' for layer in snapshot['layers']):
                                    caption += ' NEON deliveries are shown at their site locations.'
                            else:
                                caption = ('Saved map view and supported geometry layers.'
                                           if snapshot['evidence'] == 'saved-widget-state' else
                                           'Preview at the saved map center. Scene footprints were not saved in this notebook.')
                            out += [f'<div class="notebook-map" data-snapshot="../../{rel}" role="region" aria-label="Map from source cell {i+1}"></div>\n\n',
                                    f'<p class="notebook-map-caption">{caption} Drag to pan; use +/− or pinch to zoom.</p>\n\n']
                            map_count += 1
                            # The map replaces its truncated HBox object description.
                            continue
                        out += ['!!! info "Map state unavailable"\n    This cell did not save a usable map center or widget state. Save its widget state in Jupyter and rebuild the site to display a map here.\n\n']
                    if 'image/png' in data:
                        rel=f'assets/notebook-images/{slug}/cell-{i+1}-{j}.png'
                        dst=DOCS/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                        dst.write_bytes(base64.b64decode(''.join(data['image/png'])))
                        figure_count+=1
                        out += [f'![Saved figure {figure_count} from {title}, source cell {i+1}](../{rel}){{ .notebook-figure }}\n\n']
                    raw=o.get('text') or data.get('text/plain')
                    if o.get('output_type')=='error': raw=o.get('ename','Error')+': '+o.get('evalue','')
                    if raw:
                        raw=''.join(raw) if isinstance(raw,list) else raw
                        raw=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',raw)
                        if raw.startswith('<Figure size'): continue
                        if len(raw)>5000:raw=raw[:5000]+'\n… Display shortened. Full text is retained in the notebook download.'
                        out += ['???+ example "Saved output"\n\n    ```text\n'+'\n'.join('    '+line for line in raw.splitlines())+'\n    ```\n\n']
        record['figures']=figure_count
        record['maps']=map_count
        write(record['page'],''.join(out))
        dst=DOCS/'assets/notebooks'/src.name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dst)
    index='# Tutorial library\n\nRead the [curated AVIRIS-3 walkthrough](aviris3-walkthrough.md) first, then use these source notebooks as detailed worked examples. All original code, markdown, saved figures, and downloadable notebooks are retained; saved text outputs are expanded by default and can be collapsed. No notebook is executed during the build.\n\n'
    index+='## Choose a notebook\n\nFor satellites, start with the **window tutorial** when available. Whole-scene tutorials may consume substantially more memory, storage, and retrieval time. Airborne examples sample a group of flightlines but export selected windows.\n\n'
    index+='| Notebook | Cells | Saved figures | Evidence |\n|---|---:|---:|---|\n'
    for r in records:
        status='Saved outputs; not rerun' if r['outputs'] else 'No saved outputs'
        index+=f'| [{r["title"]}]({Path(r["page"]).name}) | {r["cells"]} | {r["figures"]} | {status} |\n'
    index+='\n## Before execution\n\nRead [notebook caveats](caveats.md), set your own input/output paths, begin with a bounded window, verify ancillary data, and distinguish a reused retrieval from a fresh benchmark. The package readers expect provider files, not arbitrary exported GeoTIFFs.\n'
    write('tutorials/index.md',index)
    write('assets/notebook-inventory.json',json.dumps(records,indent=2))
    return records


def main():
    groups, api=generate_api()
    notebooks=generate_notebooks()
    # Curated navigation is maintained separately from generated content.
    config=yaml.safe_load((ROOT/'mkdocs.yml').read_text())
    config['plugins']=['search',{'mkdocstrings':{'handlers':{'python':{'paths':[str(REPO)],'options':{
        'allow_inspection':False,'docstring_style':'google','docstring_section_style':'spacy',
        'docstring_options':{'warn_unknown_params':False,'warn_missing_types':False},
        'show_source':True,'show_signature_annotations':True,'signature_crossrefs':False,
        'show_symbol_type_heading':True,'heading_level':2,'show_submodules':False}}}}}]
    nav=yaml.safe_load((ROOT/'navigation.yml').read_text())
    for item in nav:
        if 'API reference' in item:
            item['API reference']=[{'Overview':'api/index.md'}]+[{g:entries} for g,entries in groups.items()]
        if 'Tutorials' in item:
            item['Tutorials'] += [{'Notebook library':[{r['title']:r['page']} for r in notebooks]}]
    config['extra_javascript'] = ['assets/vendor/leaflet/leaflet.js', 'javascripts/notebook-maps.js']
    config['extra_css'] = ['assets/vendor/leaflet/leaflet.css', 'stylesheets/extra.css']
    config['nav']=nav
    project = tomllib.loads((REPO/'pyproject.toml').read_text())['project']
    version = next(ast.literal_eval(n.value) for n in ast.parse((PKG/'__init__.py').read_text()).body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__version__' for t in n.targets))
    # both from pyproject, so there is one place to change the address
    config['site_url'] = project['urls']['Documentation']
    config['repo_url'] = project['urls']['Repository']
    config['repo_name'] = '/'.join(config['repo_url'].rstrip('/').split('/')[-2:])
    config['edit_uri'] = ''
    config['hooks'] = ['hooks.py']
    config['copyright'] = f'hyperproc {version} · MIT · Fujiang Ji'
    for name in ('LICENSE', 'CITATION.cff'):
        shutil.copyfile(REPO/name, DOCS/'assets'/name)

    (ROOT/'mkdocs.yml').write_text(yaml.safe_dump(config,sort_keys=False,allow_unicode=True,width=100))
    manifest={'source_version':version, 'python_requires':project['requires-python'],'api_modules':sum(map(len,groups.values())),
              'functions_and_classes':len(api),'notebooks':len(notebooks),
              'saved_figures':sum(r['figures'] for r in notebooks),
              'map_previews':sum(r['maps'] for r in notebooks),
              'map_recordings_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'map-recordings').rglob('*.json'))},
              'package_source_sha256':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(PKG.rglob('*.py')) if not p.name.startswith('._')},
              'metadata_source_sha256':{name:hashlib.sha256((REPO/name).read_bytes()).hexdigest() for name in ('pyproject.toml', 'LICENSE', 'CITATION.cff')},
              'execution_policy':'Static source inspection and saved-output rendering only; no hyperproc import or notebook execution.'}
    write('assets/build-manifest.json',json.dumps(manifest,indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k!='package_source_sha256'},indent=2))


if __name__=='__main__':main()
