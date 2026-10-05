# hyperproc.correct.pipeline.overlap_agreement

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def overlap_agreement(ds_a: xr.Dataset, ds_b: xr.Dataset, wavelengths=(550, 660, 850, 1650, 2200), n_points: int=20000, n_strips: int=4, seed: int=0) -> dict
```

Do two overlapping north-up cubes on one grid agree where they overlap?

Samples map coordinates inside the intersection (in a few row strips, to
keep the chunk reads bounded), takes the nearest pixel from each cube and
reports the median absolute relative difference and correlation per band.
Run it on the raw cubes and on the corrected ones: a real BRDF correction
must bring the two views of the same ground closer together.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.overlap_agreement --runtime`.
