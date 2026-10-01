"""Satellite BRDF normalisation by the c-factor method (Roy et al. 2016).

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
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import xarray as xr

from hyperproc.correct import mcd43
from hyperproc.correct.kernels import geometric_kernel, volume_kernel

__all__ = ["band_weights", "band_map", "model_reflectance", "c_factor", "nbar", "view_profile",
           "model_agreement", "lonlat_of", "angles_of"]

SPECTRAL_MODES = ("interp", "nearest")
DEFAULT_CLIP = (0.25, 4.0)
MIN_MODEL = 1e-4        # a modelled reflectance below this makes the ratio meaningless


# --------------------------------------------------------------------------- #
# mapping the seven MODIS bands onto an instrument's wavelengths               #
# --------------------------------------------------------------------------- #

def band_map(wavelength) -> np.ndarray:
    """Index (0-6) of the spectrally closest MODIS band for each wavelength (nm).

    Inside a MODIS band's nominal range that band wins; outside, the band whose
    range edge is nearest.
    """
    wl = np.atleast_1d(np.asarray(wavelength, dtype="float64"))
    lo = np.array([mcd43.MODIS_RANGES[b][0] for b in mcd43.MODIS_BANDS])
    hi = np.array([mcd43.MODIS_RANGES[b][1] for b in mcd43.MODIS_BANDS])
    inside = (wl[:, None] >= lo[None, :]) & (wl[:, None] <= hi[None, :])
    dist = np.minimum(np.abs(wl[:, None] - lo[None, :]), np.abs(wl[:, None] - hi[None, :]))
    dist = np.where(inside, -1.0, dist)
    return np.argmin(dist, axis=1)


def band_weights(wavelength, mode: str = "interp") -> np.ndarray:
    """``(7, nwl)`` weights that turn seven MODIS c-factors into per-band ones.

    Args:
        wavelength: instrument band centres in nm.
        mode: ``"interp"`` for linear interpolation between the MODIS band
            centres (constant outside them), ``"nearest"`` for the one-hot
            closest-band assignment of :func:`band_map`.

    Returns:
        A matrix whose columns sum to 1, so it is an average of the seven
        c-factors and never changes their scale.
    """
    wl = np.atleast_1d(np.asarray(wavelength, dtype="float64"))
    n = len(mcd43.MODIS_BANDS)
    w = np.zeros((n, wl.size), dtype="float32")
    if mode == "nearest":
        w[band_map(wl), np.arange(wl.size)] = 1.0
        return w
    if mode != "interp":
        raise ValueError(f"spectral must be one of {SPECTRAL_MODES}; got {mode!r}")
    centres = np.array([mcd43.MODIS_CENTRES[b] for b in mcd43.MODIS_BANDS])
    order = np.argsort(centres)
    c = centres[order]
    j = np.clip(np.searchsorted(c, wl) - 1, 0, len(c) - 2)          # left neighbour
    t = np.clip((wl - c[j]) / (c[j + 1] - c[j]), 0.0, 1.0)           # clipping = constant extrapolation
    cols = np.arange(wl.size)
    w[order[j], cols] = 1.0 - t
    w[order[j + 1], cols] += t
    return w


# --------------------------------------------------------------------------- #
# the model and the ratio                                                      #
# --------------------------------------------------------------------------- #

def model_reflectance(params, sza, vza, raa, volume: str = "ross_thick",
                      geometric: str = "li_sparse_r", b_r: float = 1.0, h_b: float = 2.0):
    """Kernel-driven reflectance from MCD43A1 weights, ``(..., 7)``.

    Args:
        params: ``(..., 7, 3)`` iso/vol/geo weights in reflectance units.
        sza, vza, raa: angles in degrees, broadcastable to ``params.shape[:-2]``.
        volume, geometric, b_r, h_b: kernel choice. The MODIS product is fitted
            with RossThick and LiSparseReciprocal at ``b_r=1, h_b=2``, so those
            are the only values that make its weights mean what they say.
    """
    params = np.asarray(params, dtype="float32")
    s = np.radians(np.asarray(sza, dtype="float32"))
    v = np.radians(np.asarray(vza, dtype="float32"))
    r = np.radians(np.asarray(raa, dtype="float32"))
    k_vol = np.asarray(volume_kernel(volume, s, v, r), dtype="float32")[..., None]
    k_geo = np.asarray(geometric_kernel(geometric, s, v, r, b_r=b_r, h_b=h_b), dtype="float32")[..., None]
    return params[..., 0] + params[..., 1] * k_vol + params[..., 2] * k_geo


def c_factor(params, sza, vza, raa, sza_ref=45.0, vza_ref=0.0, raa_ref=0.0,
             volume: str = "ross_thick", geometric: str = "li_sparse_r",
             b_r: float = 1.0, h_b: float = 2.0, clip=DEFAULT_CLIP) -> np.ndarray:
    """The per-MODIS-band correction ratio, ``(..., 7)``.

    Args:
        params: ``(..., 7, 3)`` MCD43A1 weights (NaN where the product has none).
        sza, vza, raa: observed geometry in degrees.
        sza_ref: target solar zenith. A number, ``"observed"`` to keep each
            pixel's own Sun angle, or ``"mean"`` for the scene mean.
        vza_ref, raa_ref: target view geometry, nadir by default.
        clip: ``(lo, hi)`` bounds on the ratio, or None. Ratios outside the
            bounds come from cells where the modelled reflectance at the
            observed geometry is near zero; they are clipped, not dropped.

    Returns:
        float32 ``(..., 7)``, NaN where the parameters are missing or the
        model is degenerate.
    """
    sza = np.asarray(sza, dtype="float32")
    if isinstance(sza_ref, str):
        if sza_ref == "observed":
            sza_ref = sza
        elif sza_ref == "mean":
            sza_ref = float(np.nanmean(sza))
        else:
            raise ValueError(f"sza_ref must be a number, 'observed' or 'mean'; got {sza_ref!r}")
    kw = dict(volume=volume, geometric=geometric, b_r=b_r, h_b=h_b)
    obs = model_reflectance(params, sza, vza, raa, **kw)
    ref = model_reflectance(params, np.broadcast_to(np.asarray(sza_ref, dtype="float32"), sza.shape),
                            np.full_like(sza, vza_ref), np.full_like(sza, raa_ref), **kw)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.where(obs > MIN_MODEL, ref / obs, np.nan).astype("float32")
    c[~np.isfinite(c)] = np.nan
    if clip is not None:
        c = np.clip(c, clip[0], clip[1])
    return c


# --------------------------------------------------------------------------- #
# whole-scene correction                                                       #
# --------------------------------------------------------------------------- #

def lonlat_of(ds) -> tuple:
    """Per-pixel longitude and latitude for the grid a dataset is on."""
    if "lon" in ds and "lat" in ds:
        return (np.asarray(ds["lon"].values, dtype="float64"),
                np.asarray(ds["lat"].values, dtype="float64"))
    if "x" not in ds.coords or "y" not in ds.coords:
        raise ValueError("dataset has neither lon/lat layers nor x/y coordinates")
    x = np.asarray(ds["x"].values, dtype="float64")
    y = np.asarray(ds["y"].values, dtype="float64")
    xx, yy = np.meshgrid(x, y)
    crs = str(ds.attrs.get("crs", "") or "")
    if crs and crs.upper() not in ("EPSG:4326", "OGC:CRS84"):
        from pyproj import Transformer
        lon, lat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True).transform(xx, yy)
        return np.asarray(lon), np.asarray(lat)
    return xx, yy


def angles_of(ds) -> tuple:
    """Solar zenith, view zenith and relative azimuth layers, in degrees."""
    missing = [n for n in ("sza", "vza") if n not in ds]
    if missing:
        raise ValueError(f"the dataset has no {missing} layer; BRDF normalisation needs per-pixel "
                         "geometry (open the granule with its observation file)")
    sza = np.asarray(ds["sza"].values, dtype="float32")
    vza = np.asarray(ds["vza"].values, dtype="float32")
    if "raa" in ds:
        raa = np.asarray(ds["raa"].values, dtype="float32")
    elif "vaa" in ds and "saa" in ds:
        raa = (np.asarray(ds["vaa"].values, dtype="float32") - np.asarray(ds["saa"].values, dtype="float32")) % 360.0
    else:
        raise ValueError("the dataset has neither 'raa' nor 'vaa'/'saa'; cannot build the relative azimuth")
    return sza, vza, raa


def _fill_gaps(c: np.ndarray, how: str) -> tuple:
    """Replace NaN c-factors; returns ``(filled, valid_mask)``."""
    valid = np.isfinite(c).all(axis=-1)
    if how == "none":
        return np.where(np.isfinite(c), c, 1.0).astype("float32"), valid
    if how == "median":
        med = np.nanmedian(c.reshape(-1, c.shape[-1]), axis=0)
        med = np.where(np.isfinite(med), med, 1.0).astype("float32")
        return np.where(np.isfinite(c), c, med).astype("float32"), valid
    if how == "nearest":
        from scipy.ndimage import distance_transform_edt
        out = np.array(c, dtype="float32", copy=True)
        if valid.any() and not valid.all():
            idx = distance_transform_edt(~valid, return_distances=False, return_indices=True)
            out[~valid] = c[idx[0][~valid], idx[1][~valid]]
        out[~np.isfinite(out)] = 1.0
        return out, valid
    raise ValueError(f"fill must be 'none', 'median' or 'nearest'; got {how!r}")


def nbar(ds: xr.Dataset, params=None, *, var: str | None = None,
         sza_ref=45.0, vza_ref: float = 0.0, raa_ref: float = 0.0,
         spectral: str = "nearest", volume: str = "ross_thick", geometric: str = "li_sparse_r",
         b_r: float = 1.0, h_b: float = 2.0, clip=DEFAULT_CLIP, fill: str = "none",
         qa_max: int | None = 3, mask_snow: bool = True, keep_c: bool = True,
         source: str = "gee", cache_dir=None, date: str | None = None, days: int = 8,
         res: float | None = None,
         pad: float = 0.05, project: str | None = None, sampling: str = "bilinear",
         verbose: bool = True) -> xr.Dataset:
    """Normalise a satellite reflectance cube to a common Sun/view geometry.

    Args:
        ds: a hyperproc dataset with a reflectance cube and per-pixel ``sza``,
            ``vza`` and ``raa`` (or ``vaa``/``saa``) layers, on either a map
            grid or a swath grid with ``lon``/``lat``. The L2A product of any
            of the readers qualifies, and so does the output of
            :func:`hyperproc.atmos.correct`.
        params: MCD43A1 parameters as a :class:`~hyperproc.correct.mcd43.Params`
            or a path to a stack. Downloaded for the scene when omitted.
        var: the variable to correct; the main cube by default.
        sza_ref, vza_ref, raa_ref: target geometry (see the module docstring).
        spectral: ``"nearest"`` (default, each band takes the closest MODIS
            band's c-factor) or ``"interp"`` (linear in wavelength between the
            seven, smoother but not a measured shape).
        volume, geometric, b_r, h_b: kernel choice; leave at the MODIS pair.
        clip: bounds on the c-factor, or None.
        fill: what to do where MODIS has no retrieval. ``"none"`` leaves the
            reflectance untouched (c = 1) and flags the pixel, ``"median"``
            uses the scene median c, ``"nearest"`` copies the nearest valid c.
        qa_max: keep MODIS cells whose band quality is <= this. The default 3
            keeps every retrieval; a magnitude inversion scales all three
            weights together and that factor cancels in the ratio. Pass 1 for
            full inversions only, at the cost of holes in the correction.
        mask_snow: drop cells the MODIS product flags as snow-covered.
        keep_c: attach the seven c-factors as a ``c_factor`` variable.
        source, cache_dir, date, days, pad, res, project: passed to
            :func:`hyperproc.correct.mcd43.fetch` when ``params`` is None.
            ``res=None`` lets the MODIS grid adapt to this image's own pixel
            size (see :func:`hyperproc.correct.mcd43.step_for`).
        sampling: ``"bilinear"`` or ``"nearest"`` sampling of the MODIS grid.

    Returns:
        A copy of ``ds`` with the cube replaced by the normalised one (lazy,
        so nothing is computed until it is written), a ``brdf_valid`` flag
        layer, optional ``c_factor``, and ``brdf_*`` attributes recording what
        was done. ``attrs["stem"]`` gains a ``_brdf`` suffix.

    Raises:
        ValueError: the dataset has no geometry, or an argument is out of range.
    """
    from hyperproc.io import main_var
    if spectral not in SPECTRAL_MODES:
        raise ValueError(f"spectral must be one of {SPECTRAL_MODES}; got {spectral!r}")
    var = var or main_var(ds)
    cube = ds[var]
    if "wavelength" not in cube.dims:
        raise ValueError(f"{var!r} has no wavelength dimension; nothing to normalise")

    sza, vza, raa = angles_of(ds)
    if verbose:
        print(f"BRDF c-factor on {var} {dict(cube.sizes)}: sza {np.nanmean(sza):.1f} deg, "
              f"vza {np.nanmin(vza):.1f}-{np.nanmax(vza):.1f} deg", flush=True)

    if params is None:
        params = mcd43.fetch(ds=ds, date=date, out_dir=cache_dir, source=source, days=days,
                             pad=pad, res=res, project=project, verbose=verbose)
    elif isinstance(params, (str, Path)):
        params = mcd43.read(params)
    if qa_max is not None or mask_snow:
        params = params.masked(qa_max=qa_max, snow=mask_snow)

    lon, lat = lonlat_of(ds)
    sampled = params.sample(lon, lat, method=sampling)                 # (y, x, 7, 3)
    c = c_factor(sampled, sza, vza, raa, sza_ref=sza_ref, vza_ref=vza_ref, raa_ref=raa_ref,
                 volume=volume, geometric=geometric, b_r=b_r, h_b=h_b, clip=clip)
    c, valid = _fill_gaps(c, fill)
    # An orthorectified swath sits inside a north-up box, so a large share of the grid was
    # never observed at all. Those cells are not a failure of the MODIS product and must
    # not be counted against it: coverage is quoted over the pixels the sensor did see.
    observed = np.isfinite(sza) & np.isfinite(vza) & np.isfinite(raa)
    void = float(1.0 - observed.mean())
    cover = float(valid[observed].mean()) if observed.any() else 0.0
    if verbose:
        # the median has to be taken over the corrected pixels: with fill="none" the rest
        # carry a placeholder 1.0 that would drag any whole-array statistic towards 1
        med = c[valid] if valid.any() else c
        print(f"  MODIS parameters at {cover * 100:.1f} % of the {(1 - void) * 100:.0f} % of cells "
              f"the sensor observed; c-factor median {np.nanmedian(med):.4f} "
              f"(band 2 {np.nanmedian(med[..., 1]):.4f})", flush=True)
    if cover < 0.01:
        warnings.warn("MODIS BRDF parameters cover under 1 % of the scene; the product is "
                      "essentially uncorrected (open water, permanent snow or a date with no "
                      "MODIS retrieval)", stacklevel=2)

    wl = np.asarray(cube["wavelength"].values, dtype="float64")
    weights = band_weights(wl, spectral)                               # (7, nwl)
    try:
        import dask.array as da
        rows = max(1, int(3e7 // max(1, c.shape[1] * c.shape[2])))
        c_arr = da.from_array(c, chunks=(rows, c.shape[1], c.shape[2]))
    except ImportError:                                                # pragma: no cover
        c_arr = c
    c_da = xr.DataArray(c_arr, dims=("y", "x", "modis_band"),
                        coords={"modis_band": list(mcd43.MODIS_BANDS)})
    w_da = xr.DataArray(weights, dims=("modis_band", "wavelength"),
                        coords={"modis_band": list(mcd43.MODIS_BANDS), "wavelength": cube["wavelength"]})
    c_full = xr.dot(c_da, w_da, dim="modis_band")

    out = ds.copy()
    out[var] = (cube * c_full.astype("float32")).astype("float32").transpose(*cube.dims)
    out[var].attrs.update(cube.attrs)
    out[var].attrs["long_name"] = (cube.attrs.get("long_name", "reflectance")
                                   + " normalised to a common Sun/view geometry")
    if "uncertainty" in out and out["uncertainty"].dims == cube.dims:
        out["uncertainty"] = (out["uncertainty"] * np.abs(c_full).astype("float32")).astype("float32")
    flag = np.where(observed, valid.astype("uint8"), 2).astype("uint8")
    out["brdf_valid"] = (("y", "x"), flag)
    out["brdf_valid"].attrs.update(long_name="source of the BRDF correction at this pixel",
                                   flag_values="0, 1, 2",
                                   flag_meanings="filled retrieved outside_observation")
    if keep_c:
        out["c_factor"] = (("y", "x", "modis_band"), c)
        out["c_factor"].attrs.update(long_name="BRDF c-factor per MODIS band", units="unitless")
        out = out.assign_coords(modis_band=list(mcd43.MODIS_BANDS))

    target = ("observed" if isinstance(sza_ref, str) and sza_ref == "observed"
              else f"{float(np.mean(sza_ref)):.4g}" if not isinstance(sza_ref, str) else sza_ref)
    out.attrs.update(
        brdf_method="c-factor (Roy et al. 2016) with MODIS MCD43A1 kernel weights",
        brdf_kernels=f"{volume}+{geometric} (b_r={b_r}, h_b={h_b})",
        brdf_target=f"sza={target} vza={vza_ref:g} raa={raa_ref:g}",
        brdf_spectral=spectral, brdf_fill=fill, brdf_sampling=sampling,
        brdf_clip="none" if clip is None else f"{clip[0]}-{clip[1]}",
        brdf_quality=f"qa_max={qa_max} mask_snow={mask_snow}",
        brdf_parameters=str(getattr(params, "path", "") or ""),
        brdf_parameter_date=getattr(params, "date", ""),
        brdf_parameter_step_m=f"{abs(params.transform[0]) * 111320:.0f}",
        brdf_coverage=f"{cover:.4f}", brdf_unobserved=f"{void:.4f}",
        stem=str(ds.attrs.get("stem", "scene")) + "_brdf",
    )
    return out


def view_profile(before: xr.Dataset, after: xr.Dataset | None = None, wavelength: float = 865.0,
                 var: str | None = None, step: float = 2.0, stride: int = 1,
                 ndvi: tuple | None = None) -> dict:
    """Mean reflectance against view zenith, before and after normalisation.

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
    """
    from hyperproc.io import main_var
    var = var or main_var(before)
    wls = np.asarray(before[var]["wavelength"].values, dtype="float64")
    band = int(np.argmin(np.abs(wls - wavelength)))
    sel = dict(wavelength=band)
    sl = dict(y=slice(None, None, stride), x=slice(None, None, stride))
    vza = np.asarray(before["vza"].isel(**sl).values, dtype="float64").ravel()
    r0 = np.asarray(before[var].isel(**sl).isel(**sel).values, dtype="float64").ravel()
    r1 = (np.asarray(after[var].isel(**sl).isel(**sel).values, dtype="float64").ravel()
          if after is not None else None)
    ok = np.isfinite(vza) & np.isfinite(r0) & (r0 > 0)
    if r1 is not None:
        ok &= np.isfinite(r1)
    if ndvi is not None:
        red = np.asarray(before[var].isel(**sl).isel(wavelength=int(np.argmin(np.abs(wls - 660)))).values,
                         dtype="float64").ravel()
        nir = np.asarray(before[var].isel(**sl).isel(wavelength=int(np.argmin(np.abs(wls - 860)))).values,
                         dtype="float64").ravel()
        with np.errstate(invalid="ignore", divide="ignore"):
            index = (nir - red) / (nir + red)
        ok &= np.isfinite(index) & (index >= ndvi[0]) & (index < ndvi[1])
    vza, r0 = vza[ok], r0[ok]
    r1 = r1[ok] if r1 is not None else None
    if vza.size == 0:
        raise ValueError("no valid pixels to profile")
    edges = np.arange(np.floor(vza.min()), np.ceil(vza.max()) + step, step)
    which = np.clip(np.digitize(vza, edges) - 1, 0, len(edges) - 2)
    centres, m0, m1, n = [], [], [], []
    for k in range(len(edges) - 1):
        sel_k = which == k
        if sel_k.sum() < 10:
            continue
        centres.append(0.5 * (edges[k] + edges[k + 1]))
        m0.append(float(r0[sel_k].mean()))
        m1.append(float(r1[sel_k].mean()) if r1 is not None else np.nan)
        n.append(int(sel_k.sum()))
    # A slope needs a spread to be fitted through. Several of these sensors hold the view
    # zenith fixed across a whole scene, and fitting a line to a single value returns a
    # number that means nothing at all; refuse instead of reporting it.
    span = float(np.nanmax(vza) - np.nanmin(vza))
    if len(centres) < 3 or span < 0.5:
        raise ValueError(f"the scene spans {span:.2f} deg of view zenith in {len(centres)} bin(s); "
                         "there is no across-track trend to flatten, so this test says nothing")
    out = {"wavelength": float(wls[band]), "vza": np.array(centres), "ndvi": ndvi,
           "before": np.array(m0), "count": np.array(n), "pixels": int(vza.size),
           "vza_span": span, "slope_before": float(np.polyfit(vza, r0, 1)[0])}
    if r1 is not None:
        out["after"] = np.array(m1)
        out["slope_after"] = float(np.polyfit(vza, r1, 1)[0])
    return out


def model_agreement(ds: xr.Dataset, params, wavelength: float = 865.0, var: str | None = None,
                    ndvi: tuple | None = (0.2, 0.5), vza_range: tuple | None = None,
                    step: float = 20.0, stride: int = 1, min_count: int = 200) -> dict:
    """Does the borrowed MODIS shape actually describe this scene's angular signal?

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
    """
    from hyperproc.io import main_var
    var = var or main_var(ds)
    wls = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    band = int(np.argmin(np.abs(wls - wavelength)))
    mb = int(band_map([wls[band]])[0])
    sl = dict(y=slice(None, None, stride), x=slice(None, None, stride))
    sub = ds.isel(**sl)

    sza, vza, raa = angles_of(sub)
    lon, lat = lonlat_of(sub)
    sampled = params.sample(lon, lat)
    obs = np.asarray(sub[var].isel(wavelength=band).values, dtype="float64")
    model = model_reflectance(sampled, sza, vza, raa)[..., mb]
    flipped = model_reflectance(sampled, sza, vza, (raa + 180.0) % 360.0)[..., mb]

    keep = np.isfinite(obs) & (obs > 0) & np.isfinite(model) & np.isfinite(flipped)
    if vza_range is not None:
        keep &= (vza >= vza_range[0]) & (vza <= vza_range[1])
    if ndvi is not None:
        red = np.asarray(sub[var].isel(wavelength=int(np.argmin(np.abs(wls - 660)))).values, dtype="float64")
        nir = np.asarray(sub[var].isel(wavelength=int(np.argmin(np.abs(wls - 860)))).values, dtype="float64")
        with np.errstate(invalid="ignore", divide="ignore"):
            index = (nir - red) / (nir + red)
        keep &= np.isfinite(index) & (index >= ndvi[0]) & (index < ndvi[1])
    if keep.sum() < min_count:
        raise ValueError(f"only {int(keep.sum())} pixels pass the filters; loosen ndvi= or vza_range=")

    fold = np.abs(((raa + 180.0) % 360.0) - 180.0)
    edges = np.arange(0.0, 180.0 + step, step)
    centres, o, m, f, n = [], [], [], [], []
    for i in range(len(edges) - 1):
        k = keep & (fold >= edges[i]) & (fold < edges[i + 1])
        if k.sum() < min_count:
            continue
        centres.append(0.5 * (edges[i] + edges[i + 1]))
        o.append(float(np.mean(obs[k]))); m.append(float(np.mean(model[k])))
        f.append(float(np.mean(flipped[k]))); n.append(int(k.sum()))
    if len(centres) < 3:
        raise ValueError(f"only {len(centres)} azimuth bins have {min_count}+ pixels; "
                         "this scene does not span enough azimuth to test the shape")
    o, m, f = np.array(o), np.array(m), np.array(f)
    r = float(np.corrcoef(o, m)[0, 1])
    r_flip = float(np.corrcoef(o, f)[0, 1])
    # A correlation over three bins spanning 50 degrees is noise: across a scene, azimuth
    # is also a position, so what varies between neighbouring bins is mostly land cover.
    # Only a wide azimuth span, which in practice means a wide swath, can decide anything.
    span = float(centres[-1] - centres[0]) + step        # bin centres understate the coverage by one bin
    if len(centres) < 4 or span < 90.0:
        verdict = (f"inconclusive: {span:.0f} deg of relative azimuth in {len(centres)} bins "
                   "is too little to separate the angular signal from the land cover")
    elif r > 0.5 and r - r_flip > 0.3:
        verdict = "the MODIS shape matches this scene"
    elif r_flip > 0.5 and r_flip - r > 0.3:
        verdict = "the azimuth convention looks inverted"
    else:
        verdict = "inconclusive: the scene's angular signal is weak or dominated by land cover"
    return {"wavelength": float(wls[band]), "modis_band": list(mcd43.MODIS_BANDS)[mb],
            "raa": np.array(centres), "observed": o, "modelled": m, "flipped": f,
            "count": np.array(n), "pixels": int(keep.sum()), "r": r, "r_flipped": r_flip,
            "azimuth_span": span, "verdict": verdict}
