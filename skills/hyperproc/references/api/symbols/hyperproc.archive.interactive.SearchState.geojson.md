# hyperproc.archive.interactive.SearchState.geojson

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def geojson(self) -> dict
```

The footprints as a FeatureCollection, ready for a map layer.

A footprint with no area - NEON publishes a site's coordinates, not its
flight box - comes out as a Point rather than a zero-width polygon, so
it is visible instead of invisible.

[Module and aliases](../hyperproc-archive-interactive.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.archive.interactive.SearchState.geojson --runtime`.
