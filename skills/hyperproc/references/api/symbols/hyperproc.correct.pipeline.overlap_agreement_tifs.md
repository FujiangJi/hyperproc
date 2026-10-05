# hyperproc.correct.pipeline.overlap_agreement_tifs

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def overlap_agreement_tifs(path_a, path_b, resampling: str='nearest', min_value: float=0.005) -> dict
```

Do two GeoTIFFs agree where they overlap? Both are put on a common
north-up grid over the intersection; per band: median and p90 absolute
relative difference, median ratio, correlation. The reprojected arrays
(``a``, ``b``, ``valid``) come back too, for difference maps.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.overlap_agreement_tifs --runtime`.
