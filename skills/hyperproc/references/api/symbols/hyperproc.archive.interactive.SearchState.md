# hyperproc.archive.interactive.SearchState

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

The part of the map that is not a map: a box, a result set, a selection.

Attributes:
    bbox: ``(west, south, east, north)`` of the drawn rectangle, or ``None``.
    results: the last :class:`~hyperproc.archive.results.Results`.
    selected: the granules picked out of it, in the order they were picked.

## Declared members

- [__init__](hyperproc.archive.interactive.SearchState.__init__.md)
- [set_bbox_from_geojson](hyperproc.archive.interactive.SearchState.set_bbox_from_geojson.md)
- [search](hyperproc.archive.interactive.SearchState.search.md)
- [toggle](hyperproc.archive.interactive.SearchState.toggle.md)
- [select_all](hyperproc.archive.interactive.SearchState.select_all.md)
- [clear](hyperproc.archive.interactive.SearchState.clear.md)
- [geojson](hyperproc.archive.interactive.SearchState.geojson.md)
- [bounds](hyperproc.archive.interactive.SearchState.bounds.md)
- [summary](hyperproc.archive.interactive.SearchState.summary.md)
- [__repr__](hyperproc.archive.interactive.SearchState.__repr__.md)

[Module](../hyperproc-archive-interactive.md).
