"""Cosmetic spectral smoothing.

A per-pixel optimal-estimation retrieval leaves real band-to-band structure:
on the EMIT test granule its size matches JPL's own product exactly, and on
Tanager it sits well below the retrieval's posterior uncertainty. Some
providers publish spectra with that structure removed (Planet's Tanager
reflectance is smooth to four decimals in the near infrared, which no
per-pixel retrieval produces), so a product compared against theirs can look
noisy without being wrong.

:func:`smooth_spectra` makes the same cosmetic change, explicitly and
reversibly. It never runs by itself: correction and export leave the
retrieval as it is, and the result records what was done in
``attrs["spectral_smoothing"]``.

**It is cosmetic.** Smoothing correlates neighbouring bands, so it invalidates
the posterior uncertainty and biases anything that measures narrow features:
fit absorption depths, continuum removal and spectral indices on the
unsmoothed cube.
"""
from __future__ import annotations

from contextlib import contextmanager

import numpy as np
import xarray as xr

from hyperproc.io import main_var
from hyperproc.spectral.bands import runs_of_good_bands as _runs

__all__ = ["smooth_spectra", "find_spikes", "spline_gapfill",
           "PRISMA_ARTEFACT_RANGES", "PRISMA_MASK_AFTER"]

#: Regions where PRISMA's spectral shift leaves anomalous spikes and dips around
#: the gaseous absorptions, excluded before the spline is fitted (nm).
PRISMA_ARTEFACT_RANGES = ((535, 550), (755, 780), (755, 775), (810, 855), (885, 970),
                          (1015, 1050), (1080, 1165), (1225, 1285), (1330, 1490),
                          (1685, 1700), (1725, 1750), (1780, 1960), (1990, 2030))

#: Deep water absorptions and the noisy SWIR tail, masked *after* smoothing (nm).
PRISMA_MASK_AFTER = ((1350, 1510), (1795, 2000), (2320, 2500))


def _smooth_block(a: np.ndarray, runs, window: int, order: int, method: str) -> np.ndarray:
    from scipy.signal import savgol_filter

    out = a.astype("float32", copy=True)
    for lo, hi in runs:
        seg = out[..., lo:hi]
        finite = np.isfinite(seg)
        if not finite.any():
            continue
        filled = np.where(finite, seg, np.nan)
        # a spectrum with gaps inside a run would spread NaN through the filter;
        # interpolate those few bands first, then put the NaN back afterwards
        if not finite.all():
            idx = np.arange(hi - lo)
            flat = filled.reshape(-1, hi - lo)
            for k in np.flatnonzero(~np.isfinite(flat).all(axis=1)):
                row = flat[k]
                ok = np.isfinite(row)
                if ok.sum() >= 2:
                    row[~ok] = np.interp(idx[~ok], idx[ok], row[ok])
            filled = flat.reshape(seg.shape)
        if method == "savgol":
            sm = savgol_filter(filled, window_length=window, polyorder=order, axis=-1, mode="nearest")
        elif method == "moving":
            k = np.ones(window, dtype="float32") / window
            pad = window // 2
            padded = np.pad(filled, [(0, 0)] * (filled.ndim - 1) + [(pad, pad)], mode="edge")
            sm = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), -1, padded)
        else:
            raise ValueError("method must be 'savgol' or 'moving'")
        out[..., lo:hi] = np.where(finite, sm, np.nan)
    return out


def smooth_spectra(ds: xr.Dataset, var: str | None = None, window: int = 5, order: int = 2,
                   method: str = "savgol", good_only: bool = True) -> xr.Dataset:
    """A copy of ``ds`` whose spectra are smoothed along wavelength.

    Args:
        ds: dataset with a ``(y, x, wavelength)`` cube.
        var: which variable to smooth; the cube variable by default.
        window: filter length in bands, odd, at least ``order + 2``.
        order: polynomial order for ``"savgol"``.
        method: ``"savgol"`` (Savitzky-Golay, keeps peak shape) or
            ``"moving"`` (running mean).
        good_only: smooth only runs of bands flagged usable by
            ``good_wavelength``, so the filter never reaches across the
            water-vapour gaps. With False every band is one run.

    Returns:
        A new dataset; the smoothed variable carries ``smoothing`` in its
        attrs and the dataset carries ``spectral_smoothing``. Uncertainty
        layers are dropped, because smoothing makes them wrong.
    """
    var = var or main_var(ds)
    if window % 2 == 0 or window < 3:
        raise ValueError("window must be odd and at least 3")
    if method == "savgol" and window <= order:
        raise ValueError("window must exceed order for a Savitzky-Golay filter")
    da = ds[var]
    if da.dims[-1] != "wavelength":
        da = da.transpose(..., "wavelength")
    nb = da.sizes["wavelength"]
    good = (ds["good_wavelength"].values.astype(bool) if good_only and "good_wavelength" in ds.coords
            else np.ones(nb, bool))
    runs = _runs(good, window)
    if not runs:
        raise ValueError(f"no run of {window} consecutive usable bands to smooth")
    smoothed = xr.apply_ufunc(_smooth_block, da, kwargs=dict(runs=runs, window=window, order=order, method=method),
                              input_core_dims=[["wavelength"]], output_core_dims=[["wavelength"]],
                              dask="parallelized", output_dtypes=["float32"],
                              dask_gufunc_kwargs={"allow_rechunk": True})
    out = ds.copy()
    out[var] = smoothed.transpose(*ds[var].dims)
    out[var].attrs = dict(ds[var].attrs)
    note = (f"{method} window={window}" + (f" order={order}" if method == "savgol" else "")
            + (", within usable-band runs" if good_only else "") + " (cosmetic, applied after the retrieval)")
    out[var].attrs["smoothing"] = note
    out.attrs["spectral_smoothing"] = note
    for name in ("uncertainty",):
        if name in out:
            out = out.drop_vars(name)
            out.attrs["spectral_smoothing"] += "; uncertainty dropped (no longer valid)"
    return out


# --------------------------------------------------------------------------- #
# despike, spline, gap fill: the published PRISMA route                        #
# --------------------------------------------------------------------------- #

def find_spikes(spectrum, threshold: float = 0.018, nups: int = 1,
                ndowns: int | None = None, min_height: float = -np.inf) -> np.ndarray:
    """Bands belonging to an upward spike, as R's ``pracma::findpeaks`` marks them.

    A faithful port, because reproducing a published pipeline means reproducing
    its peak finder. The sign of the first difference becomes a string of ``+``
    and ``-``, runs matching ``[+]{nups,}[-]{ndowns,}`` are peaks, and a peak
    survives when it exceeds the **higher** of its two ends by ``threshold``.

    For every surviving peak exactly three bands are marked: the peak, the band
    where its rise began and the band where its fall ended. Not the span
    between them. On a real PRISMA spectrum that is 11 to 26 bands of 230.

    Note that this finds maxima only. Downward spikes are left for the spline.

    Args:
        spectrum: one spectrum, in the order the bands are stored.
        threshold: minimum height above the higher end of the peak.
        nups, ndowns: how many rises and falls make a peak; ``ndowns`` defaults
            to ``nups``.
        min_height: peaks below this absolute value are ignored.

    Returns:
        Boolean mask, True where a band belongs to a peak.
    """
    import re
    y = np.asarray(spectrum, dtype="float64")
    mask = np.zeros(y.size, dtype=bool)
    if y.size < 3 or not np.isfinite(y).all():
        finite = np.isfinite(y)
        if finite.sum() < 3:
            return mask
        y = np.where(finite, y, np.nanmin(y[finite]))
    d = np.diff(y)
    chars = np.where(d > 0, "+", np.where(d < 0, "-", "0"))
    text = "".join(chars.tolist())
    pattern = re.compile(r"[+]{%d,}[-]{%d,}" % (int(nups), int(ndowns or nups)))
    for m in pattern.finditer(text):
        x1, x2 = m.start(), m.end()          # R's x1, x2 as zero-based indices
        segment = y[x1:x2 + 1]
        peak = x1 + int(np.argmax(segment))
        if y[peak] >= min_height and y[peak] - max(y[x1], y[x2]) >= threshold:
            mask[[peak, x1, x2]] = True
    return mask


def _in_ranges(wl: np.ndarray, ranges) -> np.ndarray:
    out = np.zeros(wl.size, dtype=bool)
    for lo, hi in ranges:
        out |= (wl >= lo) & (wl <= hi)
    return out


@contextmanager
def _one_blas_thread():
    """Fit spectra with BLAS held to a single thread.

    The spline solves one spectrum at a time, and each fit is a handful of
    dense solves on a matrix the size of the knot count - a couple of hundred
    rows. That is far below the size where threading a solve pays for itself,
    so the BLAS threads only contend for cores. On a busy machine the tax is
    not small: one Tanager spectrum that fits in 57 ms single-threaded took
    38 s with 32 OpenBLAS threads fighting over it, a factor of 665.

    Falls through quietly when threadpoolctl is not installed.
    """
    try:
        from threadpoolctl import threadpool_limits
    except ImportError:
        yield
        return
    with threadpool_limits(limits=1, user_api="blas"):
        yield


def _gapfill_block(a: np.ndarray, wl, exclude, mask_after, df, threshold, despike, min_points):
    from hyperproc.spectral._smoothspline import smooth_spline
    flat = a.reshape(-1, a.shape[-1]).astype("float64")
    out = np.full(flat.shape, np.nan, dtype="float32")
    fillmask = np.zeros(flat.shape, dtype=bool)
    after = _in_ranges(wl, mask_after)
    before = _in_ranges(wl, exclude)
    with _one_blas_thread():
        for k in range(flat.shape[0]):
            y = flat[k].copy()
            if not np.isfinite(y).any():
                continue
            drop = before.copy()
            if despike:
                drop |= find_spikes(np.nan_to_num(y, nan=float(np.nanmin(y))), threshold)
            y[drop] = np.nan
            ok = np.isfinite(y)
            if ok.sum() < min_points:
                continue
            fit = smooth_spline(wl[ok], y[ok], df=df)
            row = fit.predict(wl)
            fillmask[k] = drop & ~after
            row[after] = np.nan
            out[k] = row
    return out.reshape(a.shape), fillmask.reshape(a.shape)


def spline_gapfill(ds: xr.Dataset, var: str | None = None, df: float = 60.0,
                   threshold: float = 0.018, despike: bool = True,
                   exclude=PRISMA_ARTEFACT_RANGES, mask_after=PRISMA_MASK_AFTER,
                   min_points: int = 20, keep_fill_flag: bool = True) -> xr.Dataset:
    """Despike, mask, spline-smooth with gap filling, then mask again.

    The published PRISMA route, in four steps per spectrum:

    1. mark upward spikes with :func:`find_spikes` and blank them,
    2. blank ``exclude``, the regions where the instrument's spectral shift
       leaves artefacts around the gaseous absorptions,
    3. fit a smoothing spline with ``df`` degrees of freedom through what
       survives and evaluate it at **every** wavelength, which smooths and
       fills the blanked bands in one step,
    4. blank ``mask_after``, the deep water absorptions and the SWIR tail.

    This is not what :func:`smooth_spectra` does, and the difference is the
    point. That one filters inside runs of usable bands and never crosses a
    gap, so it cannot invent a value. This one crosses them deliberately. On a
    230-band PRISMA scene about 120 bands come out with values, and some of
    those are spline fill rather than measurement, which is what
    ``keep_fill_flag`` records.

    The spline is R's ``smooth.spline``, ported in
    :mod:`hyperproc.spectral._smoothspline` and verified against it.

    Args:
        ds: dataset with a ``(y, x, wavelength)`` cube.
        var: variable to smooth; the main cube by default.
        df: degrees of freedom for the spline.
        threshold: spike height for step 1, in reflectance units.
        despike: run step 1 at all.
        exclude: ranges blanked before fitting (nm).
        mask_after: ranges blanked after fitting (nm).
        min_points: a spectrum with fewer surviving bands is left as NaN.
        keep_fill_flag: attach ``spline_filled``, True where a reported value
            came from the spline rather than from the instrument.

    Returns:
        A copy of ``ds`` with the cube replaced, recording what was done in
        ``attrs["spline_gapfill"]``. Uncertainty is dropped: the spline
        correlates bands and invents some of them.
    """
    var = var or main_var(ds)
    da = ds[var]
    if da.dims[-1] != "wavelength":
        da = da.transpose(..., "wavelength")
    wl = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    if not 1 < df <= wl.size:
        raise ValueError(f"df must satisfy 1 < df <= {wl.size}; got {df}")

    kw = dict(wl=wl, exclude=tuple(exclude), mask_after=tuple(mask_after), df=float(df),
              threshold=float(threshold), despike=bool(despike), min_points=int(min_points))
    smoothed, filled = xr.apply_ufunc(
        _gapfill_block, da, kwargs=kw,
        input_core_dims=[["wavelength"]], output_core_dims=[["wavelength"], ["wavelength"]],
        dask="parallelized", output_dtypes=["float32", bool],
        dask_gufunc_kwargs={"allow_rechunk": True})

    out = ds.copy()
    out[var] = smoothed.transpose(*ds[var].dims)
    out[var].attrs = dict(ds[var].attrs)
    note = (f"despike(threshold={threshold:g}) + {len(exclude)} excluded ranges + "
            f"smooth.spline(df={df:g}) + {len(mask_after)} masked ranges")
    out[var].attrs["smoothing"] = note
    out.attrs["spline_gapfill"] = note
    if keep_fill_flag:
        out["spline_filled"] = filled.transpose(*ds[var].dims)
        out["spline_filled"].attrs.update(
            long_name="value came from the spline, not from the instrument",
            flag_values="0, 1", flag_meanings="measured interpolated")
    if "uncertainty" in out:
        out = out.drop_vars("uncertainty")
        out.attrs["spline_gapfill"] += "; uncertainty dropped"
    return out
