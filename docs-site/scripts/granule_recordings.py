"""Bind recorded granule metadata to a notebook's saved search-result table."""
import ast
import hashlib
import json
import re
from pathlib import Path

ROW = re.compile(r'^(\S+)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+([\d,]+M|-)\s+([\d.]+%|-)$')


def streams(cell):
    return '\n'.join(''.join(o.get('text', [])) for o in cell.get('outputs', []))


def result_context(notebook, cell_index):
    table = None
    for cell in reversed(notebook['cells'][:cell_index]):
        text = streams(cell)
        if re.search(r'^granule\s+when\s+size\s+cloud', text, re.M):
            table = text
            break
    if table is None:
        return None
    rows = []
    for line in table.splitlines():
        match = ROW.match(line.strip())
        if match:
            name, time, size, cloud = match.groups()
            rows.append({'name': name, 'time': time,
                         'size_mb': int(size[:-1].replace(',', '')) if size != '-' else None,
                         'cloud': float(cloud[:-1]) if cloud != '-' else None})
    if not rows:
        return None
    search = None
    for cell in reversed(notebook['cells'][:cell_index]):
        text = streams(cell)
        match = re.search(r'searching (\S+) \((\S+) (\S+)\):', text)
        if match:
            search = dict(zip(('collection', 'sensor', 'level'), match.groups()))
            kwargs = {}
            for field, value in re.findall(r'^\s+(bounding_box|bbox|temporal|date|cloud_cover|cloud) = (.+)$', text, re.M):
                key = {'bounding_box': 'bbox', 'temporal': 'date', 'cloud_cover': 'cloud'}.get(field, field)
                try:
                    kwargs[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    if key == 'date' and '/' in value:
                        kwargs[key] = tuple(part[:10] for part in value.split('/'))
            search['kwargs'] = kwargs
            break
    if search is None:
        return None
    source = ''.join(notebook['cells'][cell_index].get('source', []))
    key = hashlib.sha256(json.dumps({'rows': rows, 'source': source, 'sensor': search['sensor'],
                                     'level': search['level']}, sort_keys=True).encode()).hexdigest()
    return {'key': key, 'rows': rows, **search}


def recorded_snapshot(directory, context, snapshot):
    if context is None or (snapshot.get('evidence') == 'saved-widget-state' and snapshot.get('layers')):
        return snapshot
    path = Path(directory)/(context['key']+'.json')
    if not path.exists():
        return snapshot
    record = json.loads(path.read_text())
    if record.get('key') != context['key']:
        return snapshot
    granules = record.get('granules', [])
    if len(granules) != len(context['rows']):
        return snapshot
    expected = [row['name'] for row in context['rows']]
    if [g.get('saved_name') for g in granules] != expected:
        return snapshot
    snapshot = dict(snapshot)
    layers = []
    for granule in granules:
        w, s, e, n = granule['bbox']
        layer = {'name': granule['name'], 'granule': granule}
        if w == e and s == n:
            layer.update(type='marker', location=[s, w])
        else:
            layer.update(type='rectangle', locations=[[s, w], [n, e]])
        layers.append(layer)
    snapshot.update(layers=layers, evidence='matched-granule-metadata',
                    metadata_retrieved_at=record['retrieved_at'])
    return snapshot
