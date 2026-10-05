# hyperproc.correct.pipeline.find_overlapping_pair

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def find_overlapping_pair(dss, exclude_same=None)
```

``(i, j, area)`` of the pair of cubes whose footprint *polygons* overlap
most, or None. ``exclude_same(ds)`` returns a key; pairs with equal keys
are skipped (e.g. chunks of one flightline when the question is *between*
lines).

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.find_overlapping_pair --runtime`.
