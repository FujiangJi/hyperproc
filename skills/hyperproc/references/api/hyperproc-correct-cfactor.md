# hyperproc.correct.cfactor

Release baseline **0.1.2**; source `hyperproc/correct/cfactor.py`. Choose a callable below rather than loading every declaration.

Satellite BRDF normalisation by the c-factor method (Roy et al. 2016).

A single spaceborne scene sees each pixel once, so it carries no information
about how that pixel's reflectance changes with Sun and view angle: the
airborne route in :mod:`hyperproc.correct.brdf`, which fits kernel weights to
the across-track spread of a flightline group, has nothing to fit. The
c-factor method borrows the shape instead. MODIS MCD43A1 gives, for every
500 m cell, the three RossThick-LiSparseReciprocal weights of the last 16
days, and the correction is the ratio of the modelled reflectance at the
target geometry to the modelled reflectance at the observed geometry::

                f_iso + f_vol K_vol(target)   + f_geo K_geo(target)
    c(x, y, b) = ---------------------------------------------------
                f_iso + f_vol K_vol(observed) + f_geo K_geo(observed)

    rho_target = c * rho_observed

Only the ratio is used, so the absolute level of the MODIS retrieval never
enters: a bias in ``f_iso`` cancels. What does enter is the *shape*, which is
why the method is trusted well beyond MODIS's own seven bands.

    from hyperproc.correct import cfactor
    out = cfactor.nbar(ds)                      # fetches MCD43A1, corrects, returns a dataset
    out = cfactor.nbar(ds, params=p, sza_ref="observed")   # view-angle normalisation only

Target geometry
---------------
``sza_ref=45, vza_ref=0, raa_ref=0`` is the usual NBAR convention: nadir view,
a fixed Sun, comparable between scenes and dates. ``sza_ref="observed"`` keeps
each pixel's own Sun angle and removes only the view-angle effect, which is
what Roy et al. (2016) published for Landsat and is the safer choice for a
single scene, because it never extrapolates the kernel model in solar zenith.
``sza_ref="mean"`` uses the scene's mean solar zenith.

Spectral mapping
----------------
MODIS gives seven c-factors; an imaging spectrometer has hundreds of bands.
``spectral="nearest"`` (default) assigns each band to the spectrally closest
MODIS band, which is what Roy et al. published and what keeps every corrected
band traceable to one measured BRDF shape. ``spectral="interp"`` interpolates
the seven linearly in wavelength instead: the correction is then smooth, at the
cost of applying a shape no MODIS band actually measured. The difference is not
small. On the EMIT test granule the largest band-to-band jump in the c-factor
is 0.100 with ``"nearest"`` against 0.0035 with ``"interp"``, so a ``"nearest"``
product carries visible steps at the wavelengths where the assignment
switches, near 1245, 1440 and 1885 nm.

## Declared exports

`band_weights`, `band_map`, `model_reflectance`, `c_factor`, `nbar`, `view_profile`, `model_agreement`, `lonlat_of`, `angles_of`

## Imported aliases

- `mcd43` → `hyperproc.correct.mcd43`
- `geometric_kernel` → `hyperproc.correct.kernels.geometric_kernel`
- `volume_kernel` → `hyperproc.correct.kernels.volume_kernel`

## Declared callables and classes

- [band_map](symbols/hyperproc.correct.cfactor.band_map.md)
- [band_weights](symbols/hyperproc.correct.cfactor.band_weights.md)
- [model_reflectance](symbols/hyperproc.correct.cfactor.model_reflectance.md)
- [c_factor](symbols/hyperproc.correct.cfactor.c_factor.md)
- [lonlat_of](symbols/hyperproc.correct.cfactor.lonlat_of.md)
- [angles_of](symbols/hyperproc.correct.cfactor.angles_of.md)
- [_fill_gaps](symbols/hyperproc.correct.cfactor._fill_gaps.md) — internal
- [nbar](symbols/hyperproc.correct.cfactor.nbar.md)
- [view_profile](symbols/hyperproc.correct.cfactor.view_profile.md)
- [model_agreement](symbols/hyperproc.correct.cfactor.model_agreement.md)

## Constant expressions

- [SPECTRAL_MODES](constants/hyperproc.correct.cfactor.SPECTRAL_MODES.md)
- [DEFAULT_CLIP](constants/hyperproc.correct.cfactor.DEFAULT_CLIP.md)
- [MIN_MODEL](constants/hyperproc.correct.cfactor.MIN_MODEL.md)
