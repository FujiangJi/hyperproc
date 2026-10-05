# hyperproc.spectral.resampling.coverage_of

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def coverage_of(target_wl, target_fwhm, source_wl, source_fwhm, usable=None) -> np.ndarray
```

Fraction of each target band's response that the source measures.

The source is treated as covering the union of its usable bands' intervals;
the target's Gaussian response is integrated over that union. 1.0 means the
target band sits entirely inside measured wavelengths, 0.0 that none of it
does.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling.coverage_of --runtime`.
