# hyperproc.correct.pipeline.seam_check

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def seam_check(ds_a: xr.Dataset, ds_b: xr.Dataset, cor_a: xr.Dataset, cor_b: xr.Dataset, out_dir, wavelengths=(450, 550, 650, 850, 1650, 2200), max_rows: int=1200, tag: str='seam', overviews=None) -> dict
```

Do two adjacent images still mismatch where they overlap after correction?

Exports the overlap windows of both images at a few wavelengths, raw and
corrected, mosaics each pair with the first image on top (so the seam is
where any colour mismatch shows), and measures the agreement in the
overlap for both. Returns the paths and the two agreement dicts.

[Module and aliases](../hyperproc-correct-pipeline.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.pipeline.seam_check --runtime`.
