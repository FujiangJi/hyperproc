# hyperproc.archive.interactive.SearchState.set_bbox_from_geojson

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def set_bbox_from_geojson(self, geometry: dict) -> tuple
```

Take the bounds of a drawn shape, whatever shape it is.

The draw toolbar can produce a rectangle, a polygon or a circle marker;
a search takes a box, so the bounds of whatever was drawn is the honest
reading of the gesture.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.SearchState.set_bbox_from_geojson --runtime`.
