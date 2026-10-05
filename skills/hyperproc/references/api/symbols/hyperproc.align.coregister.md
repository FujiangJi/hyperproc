# hyperproc.align.coregister

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def coregister(moving: xr.Dataset, reference: xr.Dataset, *, resample: bool=False, wavelength: float=DEFAULT_WAVELENGTH, tiles: int=4, min_snr: float=3.0, max_scatter: float=1.0, force: bool=False, var: str | None=None, ref_var: str | None=None, verbose: bool=True) -> xr.Dataset
```

Measure the misalignment against a reference and correct it.

Args:
    moving, reference: projected datasets covering the same ground.
    resample: put the corrected cube on the reference's own grid. False,
        the default, only moves the georeferencing, which is exact.
    wavelength, tiles, min_snr, max_scatter, var, ref_var: see
        :func:`estimate_shift`.
    force: apply the shift even when the match is not consistent.
    verbose: print the report.

Returns:
    The corrected dataset, carrying the measurement in
    ``attrs["coregistration"]``.

Raises:
    ValueError: the match is not consistent and ``force`` is False.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align.coregister --runtime`.
