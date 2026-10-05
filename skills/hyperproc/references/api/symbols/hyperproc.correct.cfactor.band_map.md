# hyperproc.correct.cfactor.band_map

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def band_map(wavelength) -> np.ndarray
```

Index (0-6) of the spectrally closest MODIS band for each wavelength (nm).

Inside a MODIS band's nominal range that band wins; outside, the band whose
range edge is nearest.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.band_map --runtime`.
