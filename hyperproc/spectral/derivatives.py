"""Spectral derivatives, by Savitzky-Golay.

Differentiating raw reflectance amplifies noise, so the derivative comes from a
local polynomial fit rather than finite differences, and only inside runs of
usable bands: a difference taken across a water-vapour gap measures the gap.
"""
from __future__ import annotations

import warnings

import numpy as np
import xarray as xr

from hyperproc.io import main_var
from hyperproc.spectral.bands import good_bands, runs_of_good_bands as _runs

__all__ = ["derivative"]


def _derivative_block(a: np.ndarray, wl: np.ndarray, runs, order: int, window: int, poly: int) -> np.ndarray:
    from scipy.signal import savgol_filter
    out = np.full(a.shape, np.nan, dtype="float32")
    for lo, hi in runs:
        seg = a[..., lo:hi]
        finite = np.isfinite(seg)
        filled = np.where(finite, seg, np.nan)
        if not finite.all():
            idx = np.arange(hi - lo)
            flat = filled.reshape(-1, hi - lo)
            for k in np.flatnonzero(~np.isfinite(flat).all(axis=1)):
                row, ok = flat[k], np.isfinite(flat[k])
                if ok.sum() >= 2:
                    row[~ok] = np.interp(idx[~ok], idx[ok], row[ok])
            filled = flat.reshape(seg.shape)
        delta = float(np.median(np.diff(wl[lo:hi])))
        d = savgol_filter(filled, window_length=window, polyorder=poly, deriv=order,
                          delta=delta, axis=-1, mode="interp")
        out[..., lo:hi] = np.where(finite, d, np.nan)
    return out


def derivative(ds: xr.Dataset, var: str | None = None, order: int = 1, window: int = 7,
               poly: int = 2, good_only: bool = True) -> xr.Dataset:
    """The spectral derivative, by Savitzky-Golay.

    Differentiating raw reflectance amplifies noise, so the derivative is taken
    from a local polynomial fit instead of finite differences, and only inside
    runs of usable bands: a difference taken across a water-vapour gap is an
    artefact of the gap.

    Args:
        ds: dataset with a ``(y, x, wavelength)`` cube.
        var: variable name; the main cube by default.
        order: 1 for the first derivative, 2 for the second.
        window: filter length in bands, odd and greater than ``poly``.
        poly: polynomial order of the local fit.
        good_only: differentiate only within runs of usable bands.

    Returns:
        A copy of ``ds`` whose cube is d^order(reflectance)/d(wavelength)^order,
        per nm to that power.

    Raises:
        ValueError: the window is even, too short, or no run is long enough.
    """
    var = var or main_var(ds)
    if window % 2 == 0 or window < 3:
        raise ValueError("window must be odd and at least 3")
    if poly >= window:
        raise ValueError("window must exceed poly")
    if order > poly:
        raise ValueError(f"a polynomial of order {poly} has no derivative of order {order}")
    da = ds[var]
    if da.dims[-1] != "wavelength":
        da = da.transpose(..., "wavelength")
    wl = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    good = (np.asarray(ds["good_wavelength"].values, dtype=bool)
            if good_only and "good_wavelength" in ds.coords else np.ones(wl.size, bool))
    runs = _runs(good, window)
    if not runs:
        raise ValueError(f"no run of {window} consecutive usable bands to differentiate")
    spacing = [np.diff(wl[lo:hi]) for lo, hi in runs]
    spread = max((float(np.ptp(s) / np.median(s)) if np.median(s) else 0.0) for s in spacing)
    if spread > 0.05:
        warnings.warn(f"band spacing varies by {spread:.0%} within a run; the Savitzky-Golay "
                      "derivative assumes even spacing, so treat the magnitude as approximate",
                      stacklevel=2)
    result = xr.apply_ufunc(_derivative_block, da,
                            kwargs=dict(wl=wl, runs=runs, order=order, window=window, poly=poly),
                            input_core_dims=[["wavelength"]], output_core_dims=[["wavelength"]],
                            dask="parallelized", output_dtypes=["float32"],
                            dask_gufunc_kwargs={"allow_rechunk": True})
    out = ds.copy()
    out[var] = result.transpose(*ds[var].dims)
    note = f"Savitzky-Golay order {order}, window {window}, poly {poly}, within usable-band runs"
    out[var].attrs = dict(ds[var].attrs)
    out[var].attrs.update(long_name=f"spectral derivative (order {order})",
                          units=f"reflectance / nm^{order}" if order > 1 else "reflectance / nm",
                          derivative=note)
    out.attrs["spectral_derivative"] = note
    for name in ("uncertainty",):
        if name in out:
            out = out.drop_vars(name)
    return out
