# hyperproc.io.envi_header

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def envi_header(ds: xr.Dataset, var: str | None=None) -> dict
```

The spectral fields an ENVI header carries and a GeoTIFF cannot.

A GeoTIFF can only label a band with free text, so ``650.4 nm`` is a
description a human reads. An ENVI header states ``wavelength``, ``fwhm``
and ``bbl`` as fields that ENVI, Spectronon and this package's own readers
parse back into numbers. That is the reason to write ENVI at all.

``bbl`` follows ENVI's convention: 1 for a usable band, 0 for one to
ignore, taken from ``good_wavelength``. Exporting a bad-band list is
something the GeoTIFF route cannot do.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.envi_header --runtime`.
