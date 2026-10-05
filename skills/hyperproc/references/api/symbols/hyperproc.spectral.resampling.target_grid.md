# hyperproc.spectral.resampling.target_grid

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def target_grid(source_wl=None, source_fwhm=None, *, step=None, fwhm=None, wl_range=None, wavelengths=None, like=None, sensor=None) -> dict
```

Resolve the many ways of naming a target band set into one description.

Exactly one of ``step``, ``wavelengths``, ``like`` or ``sensor`` is used.

Returns:
    dict with ``wavelength``, ``fwhm``, ``label`` and, for an instrument
    with a measured response, ``response`` and ``response_wl``.

[Module and aliases](../hyperproc-spectral-resampling.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.resampling.target_grid --runtime`.
