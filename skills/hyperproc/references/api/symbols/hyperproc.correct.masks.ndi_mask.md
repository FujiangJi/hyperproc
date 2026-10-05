# hyperproc.correct.masks.ndi_mask

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def ndi_mask(band_a, band_b, lo=0.1, hi=1.0)
```

True where ``lo <= NDI(a, b) <= hi`` - e.g. NDVI from 850 and 660 nm.

[Module and aliases](../hyperproc-correct-masks.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.masks.ndi_mask --runtime`.
