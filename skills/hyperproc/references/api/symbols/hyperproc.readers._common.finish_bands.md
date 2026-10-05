# hyperproc.readers._common.finish_bands

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def finish_bands(ds: xr.Dataset, *, index=None, good=None, good_source: str | None=None, fill_value=None, stem: str | None=None, datetime: str | None=None) -> None
```

Complete the band/attribute contract every reader promises.

Sets what is still missing: ``band_index`` (0-based position of each band
in the source file - ``index`` after any subsetting, else 0..n-1),
``good_wavelength`` (``good`` from the provider, else the package's
water-window default), ``fill_value`` (the source no-data value),
``stem`` (defaults to ``granule``) and ``datetime``. Never overwrites a
value a reader already set, so calling it is always safe.

[Module and aliases](../hyperproc-readers-_common.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers._common.finish_bands --runtime`.
