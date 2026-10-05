# hyperproc.spectral.resampling.build_fwhm

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def build_fwhm(centres) -> np.ndarray
```

FWHM assumed equal to the spacing between neighbouring band centres.

This is only a fallback for a band set that does not state its own widths.
It is wrong for every sensor in this package, which are all oversampled:
EMIT's bands are 8.4 nm wide at 7.44 nm spacing, DESIS's up to 6.6 nm wide
at 2.56 nm spacing. Pass the real FWHM whenever the metadata has it.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling.build_fwhm --runtime`.
