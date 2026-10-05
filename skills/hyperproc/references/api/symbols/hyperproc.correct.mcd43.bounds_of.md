# hyperproc.correct.mcd43.bounds_of

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def bounds_of(ds) -> tuple
```

Geographic bounds ``(w, s, e, n)`` of a hyperproc dataset, in degrees.

Uses the per-pixel ``lon``/``lat`` layers when the dataset has them (swath
grids), otherwise the map grid, reprojected to EPSG:4326 if needed.

[Module and aliases](../hyperproc-correct-mcd43.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.mcd43.bounds_of --runtime`.
