# hyperproc.correct.cfactor.model_agreement

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def model_agreement(ds: xr.Dataset, params, wavelength: float=865.0, var: str | None=None, ndvi: tuple | None=(0.2, 0.5), vza_range: tuple | None=None, step: float=20.0, stride: int=1, min_count: int=200) -> dict
```

Does the borrowed MODIS shape actually describe this scene's angular signal?

The whole method rests on one assumption: that the angular response MODIS
measured over 16 days at 500 m applies to what this sensor saw in one
overpass. This checks it directly, and it is the check to trust when the
view-zenith profile cannot be trusted.

Pixels are binned by relative azimuth folded to 0-180 degrees, where 0 is
the hotspot (sensor looking from the Sun's direction) and 180 is forward
scattering, holding vegetation density and view zenith roughly constant.
In each bin the mean observed reflectance is compared with the mean
reflectance the MODIS parameters predict at that same geometry. If the
shape transfers, the two rise and fall together.

The same comparison is repeated with the azimuth turned by 180 degrees.
That is a convention check with a sharp answer: relative azimuth is the one
input whose sign or origin a reader can plausibly get wrong, and a scene
that prefers the flipped version is telling you the geometry is backwards,
not that the surface is unusual.

Args:
    ds: the observed reflectance with geometry (before normalisation).
    params: the MCD43A1 :class:`~hyperproc.correct.mcd43.Params`.
    wavelength: band to test, nm. The MODIS band covering it is used.
    var: variable name; the main cube by default.
    ndvi: restrict to one vegetation-density class, or None for all pixels.
    vza_range: restrict to a view-zenith range, or None (the default) for
        all. Narrow-swath sensors sit at a single view zenith, so a fixed
        window here silently empties the test.
    step: azimuth bin width, degrees.
    stride: subsample step in y and x.
    min_count: bins with fewer pixels than this are dropped.

Returns:
    dict with ``raa`` bin centres, ``observed``, ``modelled``, ``count``,
    the correlation ``r`` across bins, ``r_flipped`` for the 180-degree
    alternative, and ``verdict``.

[Module and aliases](../hyperproc-correct-cfactor.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.correct.cfactor.model_agreement --runtime`.
