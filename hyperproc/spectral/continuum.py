"""Continuum removal by the upper convex hull.

Dividing a spectrum by its own hull separates the shape of an absorption from
the brightness of the surface under it, which is what makes a feature depth
comparable between scenes and between sensors.

The hull is fitted inside each run of usable bands, never across one, so it
cannot invent a continuum over a region the instrument does not see.
"""
from __future__ import annotations

import numpy as np
import xarray as xr

from hyperproc.io import main_var
from hyperproc.spectral.bands import good_bands, runs_of_good_bands as _runs

__all__ = ["continuum_removal"]


def _upper_hull(a: np.ndarray, wl: np.ndarray) -> np.ndarray:
    """Upper convex hull of each spectrum, evaluated at every wavelength.

    A monotone chain, run for every pixel at once: the stack is an index array
    and the "pop" step is a masked update, so the cost is a few hundred
    vector operations rather than a Python loop over millions of spectra.
    """
    flat = a.reshape(-1, a.shape[-1]).astype("float64", copy=True)
    n, nb = flat.shape
    if nb < 2:
        return a
    bad = ~np.isfinite(flat)
    if bad.any():                       # interpolate gaps so the hull is defined, restore later
        idx = np.arange(nb)
        for k in np.flatnonzero(bad.any(axis=1)):
            row, ok = flat[k], ~bad[k]
            if ok.sum() >= 2:
                row[~ok] = np.interp(idx[~ok], idx[ok], row[ok])
            elif ok.sum() == 1:
                row[~ok] = row[ok][0]
            else:
                row[:] = 0.0
    stack = np.zeros((n, nb), dtype=np.int32)
    top = np.zeros(n, dtype=np.int32)          # index of the last entry in each stack
    rows = np.arange(n)
    for i in range(1, nb):
        while True:
            active = top >= 1
            if not active.any():
                break
            i1 = stack[rows, top]
            i2 = stack[rows, np.maximum(top - 1, 0)]
            # pop while the last point sits below the chord from i2 to i
            cross = ((wl[i1] - wl[i2]) * (flat[rows, i] - flat[rows, i2])
                     - (flat[rows, i1] - flat[rows, i2]) * (wl[i] - wl[i2]))
            pop = active & (cross >= 0)
            if not pop.any():
                break
            top[pop] -= 1
        top += 1
        stack[rows, top] = i
    hull = np.empty_like(flat)
    for k in range(n):
        s = stack[k, :top[k] + 1]
        hull[k] = np.interp(wl, wl[s], flat[k, s])
    return hull.reshape(a.shape)


def _continuum_block(a: np.ndarray, wl: np.ndarray, runs) -> np.ndarray:
    out = np.full(a.shape, np.nan, dtype="float32")
    for lo, hi in runs:
        seg = a[..., lo:hi]
        hull = _upper_hull(seg, wl[lo:hi])
        with np.errstate(divide="ignore", invalid="ignore"):
            cr = np.where(np.abs(hull) > 1e-12, seg / hull, np.nan)
        out[..., lo:hi] = np.where(np.isfinite(seg), cr, np.nan)
    return out


def continuum_removal(ds: xr.Dataset, var: str | None = None, window: tuple | None = None,
                      good_only: bool = True) -> xr.Dataset:
    """Divide each spectrum by its upper convex hull.

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
    """
    var = var or main_var(ds)
    da = ds[var]
    if da.dims[-1] != "wavelength":
        da = da.transpose(..., "wavelength")
    wl = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    good = (np.asarray(ds["good_wavelength"].values, dtype=bool)
            if good_only and "good_wavelength" in ds.coords else np.ones(wl.size, bool))
    if window is not None:
        good = good & (wl >= window[0]) & (wl <= window[1])
    runs = _runs(good, 3)
    if not runs:
        raise ValueError("no run of three usable bands to fit a continuum to"
                         + (f" inside {window[0]:g}-{window[1]:g} nm" if window else ""))
    removed = xr.apply_ufunc(_continuum_block, da, kwargs=dict(wl=wl, runs=runs),
                             input_core_dims=[["wavelength"]], output_core_dims=[["wavelength"]],
                             dask="parallelized", output_dtypes=["float32"],
                             dask_gufunc_kwargs={"allow_rechunk": True})
    out = ds.copy()
    out[var] = removed.transpose(*ds[var].dims)
    note = ("upper convex hull per spectrum, within usable-band runs"
            + (f", {window[0]:g}-{window[1]:g} nm" if window else ""))
    out[var].attrs = dict(ds[var].attrs)
    out[var].attrs.update(long_name="continuum-removed reflectance", units="unitless", continuum_removal=note)
    out.attrs["continuum_removal"] = note
    for name in ("uncertainty",):
        if name in out:
            out = out.drop_vars(name)
    return out
