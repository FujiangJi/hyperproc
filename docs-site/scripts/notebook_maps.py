"""Extract browser map snapshots from saved notebook data, without executing code."""
import ast
import math
import re

WIDGET_VIEW = 'application/vnd.jupyter.widget-view+json'
WIDGET_STATE = 'application/vnd.jupyter.widget-state+json'


def coordinate(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
        return None
    return list(value) if -90 <= value[0] <= 90 and -180 <= value[1] <= 180 else None


def model_refs(value):
    if isinstance(value, str) and value.startswith('IPY_MODEL_'):
        yield value[len('IPY_MODEL_'):]
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from model_refs(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from model_refs(item)


def map_snapshot(notebook, data):
    """Return saved map geometry or a clearly labeled saved-center preview."""
    models = notebook.get('metadata', {}).get('widgets', {}).get(WIDGET_STATE, {}).get('state', {})
    root = data.get(WIDGET_VIEW, {}).get('model_id')
    pending, seen = [root], set()
    selected = None
    while pending:
        identifier = pending.pop()
        if identifier in seen or identifier not in models:
            continue
        seen.add(identifier)
        model = models[identifier]
        state = model.get('state', {})
        if model.get('model_name', state.get('_model_name')) == 'LeafletMapModel':
            selected = state
            break
        pending.extend(model_refs(state.get('children', [])))
    if selected is not None and coordinate(selected.get('center')):
        zoom = selected.get('zoom', 8)
        if isinstance(zoom, bool) or not isinstance(zoom, (int, float)) or not math.isfinite(zoom):
            zoom = 8
        layers = []
        seen = set()
        pending = list(model_refs(selected.get('layers', [])))
        types = {'LeafletPolygonModel': 'polygon', 'LeafletRectangleModel': 'rectangle',
                 'LeafletPolylineModel': 'polyline', 'LeafletMarkerModel': 'marker',
                 'LeafletCircleMarkerModel': 'marker', 'LeafletGeoJSONModel': 'geojson'}
        while pending:
            identifier = pending.pop()
            if identifier in seen or identifier not in models:
                continue
            seen.add(identifier)
            model = models[identifier]; state = model.get('state', {})
            name = model.get('model_name', state.get('_model_name'))
            pending.extend(model_refs(state.get('layers', [])))
            kind = types.get(name)
            if kind is None:
                continue
            layer = {'type': kind, 'name': str(state.get('name', ''))}
            if kind == 'geojson':
                geometry = state.get('data')
                if not isinstance(geometry, dict):
                    continue
                layer['data'] = geometry
            elif kind == 'marker':
                location = coordinate(state.get('location'))
                if location is None:
                    continue
                layer['location'] = location
            else:
                locations = state.get('locations', state.get('bounds'))
                if not isinstance(locations, list) or not locations:
                    continue
                layer['locations'] = locations
            layers.append(layer)
        return {'center': coordinate(selected['center']), 'zoom': max(1, min(18, zoom)),
                'layers': layers, 'evidence': 'saved-widget-state'}
    # The archived ipyleaflet repr is truncated but its center is retained.
    raw = data.get('text/plain', '')
    raw = ''.join(raw) if isinstance(raw, list) else raw
    match = re.search(r'Map\(center=(\[[^\]]+\]|\([^\)]+\))', raw)
    if match:
        try:
            center = coordinate(ast.literal_eval(match[1]))
        except (SyntaxError, ValueError):
            center = None
        if center is not None:
            return {'center': center, 'zoom': 8, 'layers': [], 'evidence': 'saved-center-only'}
    return None
