# hyperproc.spectral.continuum.continuum_removal

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def continuum_removal(ds: xr.Dataset, var: str | None=None, window: tuple | None=None, good_only: bool=True) -> xr.Dataset
```

Divide each spectrum by its upper convex hull.

The hull is fitted within each run of usable bands, so it never spans a
water-vapour gap and invent a continuum across a region the instrument
cannot see. Outside the fitted runs the result is NaN.

Args:
    ds: dataset with a ``(y, x, wavelength)`` cube.
    var: variable name; the main cube by default.
    window: restrict to ``(lo, hi)`` nm, which is what an absorption
        feature wants. None uses the whole spectrum.
    good_only: fit only within runs of bands flagged usable.

Returns:
    A copy of ``ds`` whose cube is the continuum-removed spectrum, 1 on
    the hull and below 1 inside an absorption.

[Module and aliases](../hyperproc-spectral-continuum.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.spectral.continuum.continuum_removal --runtime`.
