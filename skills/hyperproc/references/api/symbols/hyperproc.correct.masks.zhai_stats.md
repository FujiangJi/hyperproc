# hyperproc.correct.masks.zhai_stats

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def zhai_stats(blue, green, red, nir, swir1=None, swir2=None, valid=None)
```

The scene statistics Zhai's adaptive thresholds are built from.

Returns a dict (``ci2_mean, ci2_max, csi_min, csi_mean, blue_min,
blue_mean, n``) that :func:`zhai_cloud` accepts as ``stats`` so a mask
computed block by block, or on a subsample, uses one scene-wide set of
thresholds; the numbers also belong in a coefficient file's provenance.

[Module and aliases](../hyperproc-correct-masks.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.masks.zhai_stats --runtime`.
