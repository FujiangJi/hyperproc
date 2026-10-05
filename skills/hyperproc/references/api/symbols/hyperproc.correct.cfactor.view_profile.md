# hyperproc.correct.cfactor.view_profile

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def view_profile(before: xr.Dataset, after: xr.Dataset | None=None, wavelength: float=865.0, var: str | None=None, step: float=2.0, stride: int=1, ndvi: tuple | None=None) -> dict
```

Mean reflectance against view zenith, before and after normalisation.

A BRDF normalisation that works flattens the across-track brightness trend,
so this is the self-consistency check a single scene can supply. It has one
trap, and the trap gets worse the wider the swath: view zenith is a
function of position, so the profile is also a transect across the scene,
and what changes along it is largely the land cover, not the geometry. On a
PACE granule, where view zenith runs from 22 to 71 degrees across a
continent, the raw profile says almost nothing about BRDF.

``ndvi=(lo, hi)`` restricts the profile to pixels in one vegetation-density
class, which holds the surface roughly constant so the remaining trend is
angular. That is the version worth believing.

Args:
    before, after: the datasets to profile; ``after`` may be None.
    wavelength: band to profile, nm.
    var: variable name; the main cube by default.
    step: view-zenith bin width, degrees.
    stride: subsample step in y and x, to keep the read cheap.
    ndvi: keep only pixels whose NDVI (from the bands nearest 660 and
        860 nm of ``before``) falls in this range.

Returns:
    dict with ``vza`` bin centres, ``before``, ``after`` (when given), the
    pixel ``count`` per bin, and the linear ``slope_before`` /
    ``slope_after`` in reflectance per degree.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.view_profile --runtime`.
