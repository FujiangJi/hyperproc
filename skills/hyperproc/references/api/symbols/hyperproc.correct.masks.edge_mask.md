# hyperproc.correct.masks.edge_mask

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def edge_mask(valid, radius)
```

True for valid pixels at least ``radius`` pixels from the swath edge.

Erodes the valid footprint: the outermost pixels
of a flightline carry the strongest view-angle extremes and the most
resampling artefacts, and the BRDF fit is better without them.

[Module and aliases](../hyperproc-correct-masks.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.masks.edge_mask --runtime`.
