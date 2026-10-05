# hyperproc.correct.brdf.dynamic_bins

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def dynamic_bins(ndvi, num_bins=18, ndvi_min=0.05, ndvi_max=1.0, perc_min=10, perc_max=95, second_split=True)
```

NDVI bin edges as percentiles of the pooled sample (Queally et al. 2022).

``num_bins - 1`` percentiles are taken evenly between ``perc_min`` and
``perc_max`` of the NDVI values above zero, then ``ndvi_min`` and
``ndvi_max`` are added as the outer edges. ``second_split`` additionally
splits any bin wider than a threshold that shrinks with the bin count
(``0.43125 - 0.015625 * (n - 1)``) at that bin's median, as the reference
implementation of the method does.

Returns:
    list of ``[lo, hi]`` pairs, ascending and contiguous.

[Module and aliases](../hyperproc-correct-brdf.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.brdf.dynamic_bins --runtime`.
