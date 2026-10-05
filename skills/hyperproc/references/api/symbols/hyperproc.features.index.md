# hyperproc.features.index

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def index(ds: xr.Dataset, formula: str, var: str | None=None, tolerance: float=TOLERANCE, good_only: bool=True, name: str | None=None) -> xr.DataArray
```

Evaluate a spectral index written over wavelengths.

Args:
    ds: dataset with a wavelength cube.
    formula: a name from :data:`INDICES` (``"NDVI"``) or an expression in
        which ``R<wavelength>`` means the band nearest that wavelength in
        nm, for example ``"(R800 - R670) / (R800 + R670)"``. Arithmetic,
        and the functions log, log10, sqrt, exp and abs, are allowed;
        nothing else is, so a formula from a paper is safe to paste.
    var: variable name; the main cube by default.
    tolerance: how far each band may sit from its requested wavelength.
    good_only: ignore bands flagged unusable.
    name: name for the result; the index name or ``"index"``.

Returns:
    A lazy 2-D DataArray recording the formula and the wavelengths it
    actually used in ``attrs``.

Raises:
    ValueError: the formula names no bands, uses something not allowed, or
        asks for a wavelength this sensor does not cover.

[Module and aliases](../hyperproc-features.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.features.index --runtime`.
