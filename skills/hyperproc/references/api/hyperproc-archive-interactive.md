# hyperproc.archive.interactive

Release baseline **0.1.2**; source `hyperproc/archive/interactive.py`. Choose a callable below rather than loading every declaration.

Draw a box on a map, search it, click the footprints you want.

    >>> import hyperproc as hp
    >>> m = hp.search_map()      # displays; draw a rectangle with the toolbar
    >>> m                        # in Jupyter the map is the cell output
    >>> m.search("EMIT", "L2A", date=("2023-04-01", "2023-04-30"))
    >>> m.selected               # what you clicked
    >>> hp.download(m.selected, "data/")

Everything the panel does is a method you can call instead, and everything a
method does the panel can do, so a notebook can start by pointing and end by
scripting. The map needs ``ipyleaflet``::

    pip install 'hyperproc[search-map]'

The logic underneath - which box, which granules, which of them are selected -
is :class:`SearchState`, which needs no widgets at all.

## Imported aliases

- `_search` → `hyperproc.archive.api.search`
- `COLLECTIONS` → `hyperproc.archive.collections.COLLECTIONS`
- `resolve` → `hyperproc.archive.collections.resolve`
- `Granule` → `hyperproc.archive.results.Granule`
- `Results` → `hyperproc.archive.results.Results`

## Declared callables and classes

- [has_cloud](symbols/hyperproc.archive.interactive.has_cloud.md)
- [sensors](symbols/hyperproc.archive.interactive.sensors.md)
- [zoom_for](symbols/hyperproc.archive.interactive.zoom_for.md)
- [_flatten](symbols/hyperproc.archive.interactive._flatten.md) — internal
- [_px](symbols/hyperproc.archive.interactive._px.md) — internal
- [_widgets](symbols/hyperproc.archive.interactive._widgets.md) — internal
- [search_map](symbols/hyperproc.archive.interactive.search_map.md)
- [SearchState](symbols/hyperproc.archive.interactive.SearchState.md)
- [Map](symbols/hyperproc.archive.interactive.Map.md)

## Constant expressions

- [FOUND](constants/hyperproc.archive.interactive.FOUND.md)
- [PICKED](constants/hyperproc.archive.interactive.PICKED.md)
