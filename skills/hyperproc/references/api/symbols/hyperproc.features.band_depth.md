# hyperproc.features.band_depth

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def band_depth(ds: xr.Dataset, feature, var: str | None=None, good_only: bool=True) -> xr.Dataset
```

Depth, position and area of an absorption feature.

The continuum is the upper hull fitted inside the feature window, so the
depth is measured against the shoulders rather than against an absolute
reflectance, which is what makes it comparable between scenes.

Args:
    ds: dataset with a wavelength cube.
    feature: a name from :data:`FEATURES` (``"cellulose"``) or a
        ``(lo, hi)`` window in nm.
    var: variable name; the main cube by default.
    good_only: fit only within runs of usable bands.

Returns:
    A Dataset with ``depth`` (1 - the minimum of the continuum-removed
    spectrum), ``position`` (wavelength of that minimum, nm) and ``area``
    (integral of 1 - CR over the window, nm).

[Module and aliases](../hyperproc-features.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.features.band_depth --runtime`.
