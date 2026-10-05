# hyperproc.align.estimate_shift

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def estimate_shift(moving: xr.Dataset, reference: xr.Dataset, wavelength: float=DEFAULT_WAVELENGTH, tiles: int=4, min_snr: float=3.0, max_scatter: float=1.0, var: str | None=None, ref_var: str | None=None, verbose: bool=False) -> dict
```

How far ``moving`` sits from ``reference``, and whether to believe it.

Args:
    moving, reference: projected datasets covering the same ground.
    wavelength: band used for matching, nm.
    tiles: tile grid for the consistency check; 0 skips it.
    min_snr: below this the whole-scene peak is not trusted.
    max_scatter: tiles must agree to within this many pixels (median
        absolute deviation) for the result to count as consistent.
    var, ref_var: variable names; the main cube of each by default.
    verbose: print the report as it is produced.

Returns:
    dict with ``dy``/``dx`` in reference pixels, ``dy_m``/``dx_m`` in the
    reference's map units, ``snr``, ``scatter``, ``tiles_kept``,
    ``consistent`` and a human-readable ``report``.

Raises:
    ValueError: the two do not overlap, or are not projected.

[Module and aliases](../hyperproc-align.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.align.estimate_shift --runtime`.
