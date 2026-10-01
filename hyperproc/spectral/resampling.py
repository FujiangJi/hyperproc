"""Spectral resampling: put a cube, or a spectrum, on another band set.

Resampling is a fixed linear map. Once the weights are known, moving a whole
cube is one matrix multiply, which is why nothing here loops over pixels::

    import hyperproc as hp
    hp.resample(ds, step=10)                       # a 10 nm grid
    hp.resample(ds, step=10, fwhm=15)              # 10 nm spacing, 15 nm bands
    hp.resample(ds, like=other)                    # match another sensor's bands
    hp.resample(ds, sensor="SENTINEL2A")           # a real instrument
    hp.resample(spectra, source_wl=wl, step=10)    # an array of spectra, same maths

Two numbers, not one
--------------------
"Spectral resolution" is two independent things and every sensor in this
package has them different: the **spacing** between band centres and the
**FWHM** of each band. EMIT samples every 7.44 nm with 8.4 nm bands, PRISMA
every 9.25 nm with bands from 8.9 to 15.3 nm. So ``step`` and ``fwhm`` are
separate arguments, and leaving ``fwhm`` out makes it equal to ``step``, the
contiguous convention.

Two guards
----------
**Coverage.** A target band whose response falls partly outside the source's
range, or into a water-vapour gap, is reported with the fraction of its
response that the source actually measured, and becomes NaN below
``min_coverage``. Renormalising over whatever bands happened to be there is
the default behaviour of most implementations and it silently turns a 43 %
sample into a confident-looking number.

**Sharpening.** Resampling cannot raise spectral resolution. Asking EMIT, with
8.4 nm bands, for a 2 nm grid interpolates and calls it measurement, so it is
refused unless ``allow_sharpening=True``.

Methods
-------
``"gaussian"``
    Both source and target bands are Gaussians of their own FWHM, and the
    weight is their overlap integral, which has a closed form. The default.
``"box"``
    Source band as a rectangle of its FWHM, target as a Gaussian, weights from
    the overlap. This is what Spectral Python's ``BandResampler`` does, kept so
    earlier results stay reproducible.
``"response"``
    Uses a measured response function per target band. See
    :mod:`hyperproc.spectral.srf` for the instruments that ship one.
``"linear"``, ``"cubic"``, ``"nearest"``
    Interpolation at the target centres, ignoring band width. Right when the
    FWHM is unknown, or when the target bands are no wider than the source.
"""
from __future__ import annotations

import warnings

import numpy as np
import xarray as xr

from hyperproc.io import main_var
from hyperproc.spectral.bands import good_bands

__all__ = ["METHODS", "build_fwhm", "resampling_matrix", "resample", "target_grid"]

METHODS = ("gaussian", "box", "response", "linear", "cubic", "nearest")

SQRT_8LN2 = 2.3548200450309493          # FWHM = sigma * sqrt(8 ln 2)
_trapz = getattr(np, "trapezoid", None) or np.trapz      # renamed in numpy 2.0


def _sigma(fwhm) -> np.ndarray:
    return np.asarray(fwhm, dtype="float64") / SQRT_8LN2


def _normal_cdf(x):
    from scipy.special import erf
    return 0.5 * (1.0 + erf(np.asarray(x, dtype="float64") / np.sqrt(2.0)))


def build_fwhm(centres) -> np.ndarray:
    """FWHM assumed equal to the spacing between neighbouring band centres.

    This is only a fallback for a band set that does not state its own widths.
    It is wrong for every sensor in this package, which are all oversampled:
    EMIT's bands are 8.4 nm wide at 7.44 nm spacing, DESIS's up to 6.6 nm wide
    at 2.56 nm spacing. Pass the real FWHM whenever the metadata has it.
    """
    c = np.asarray(centres, dtype="float64")
    if c.size < 2:
        raise ValueError("need at least two band centres to infer a FWHM")
    fwhm = np.empty_like(c)
    fwhm[0] = c[1] - c[0]
    fwhm[-1] = c[-1] - c[-2]
    fwhm[1:-1] = (c[2:] - c[:-2]) / 2.0
    return np.abs(fwhm)


# --------------------------------------------------------------------------- #
# how much of a target band the source actually measured                       #
# --------------------------------------------------------------------------- #

def _merged_intervals(lo: np.ndarray, hi: np.ndarray) -> list:
    """Union of [lo, hi] intervals, merged and sorted."""
    if lo.size == 0:
        return []
    order = np.argsort(lo)
    out = [[float(lo[order[0]]), float(hi[order[0]])]]
    for k in order[1:]:
        a, b = float(lo[k]), float(hi[k])
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def coverage_of(target_wl, target_fwhm, source_wl, source_fwhm, usable=None) -> np.ndarray:
    """Fraction of each target band's response that the source measures.

    The source is treated as covering the union of its usable bands' intervals;
    the target's Gaussian response is integrated over that union. 1.0 means the
    target band sits entirely inside measured wavelengths, 0.0 that none of it
    does.
    """
    t_wl = np.atleast_1d(np.asarray(target_wl, dtype="float64"))
    t_sig = _sigma(np.broadcast_to(np.atleast_1d(target_fwhm), t_wl.shape))
    s_wl = np.asarray(source_wl, dtype="float64")
    s_fw = np.asarray(source_fwhm, dtype="float64")
    keep = np.ones(s_wl.size, bool) if usable is None else np.asarray(usable, bool)
    spans = _merged_intervals(s_wl[keep] - s_fw[keep] / 2.0, s_wl[keep] + s_fw[keep] / 2.0)
    out = np.zeros(t_wl.size, dtype="float64")
    for a, b in spans:
        out += _normal_cdf((b - t_wl) / t_sig) - _normal_cdf((a - t_wl) / t_sig)
    return np.clip(out, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# the weights                                                                  #
# --------------------------------------------------------------------------- #

def _weights_gaussian(s_wl, s_fw, t_wl, t_fw) -> np.ndarray:
    """Overlap integral of two Gaussians: a Gaussian in the centre difference."""
    var = _sigma(t_fw)[:, None] ** 2 + _sigma(s_fw)[None, :] ** 2
    d = t_wl[:, None] - s_wl[None, :]
    return np.exp(-0.5 * d ** 2 / var) / np.sqrt(var)


def _weights_box(s_wl, s_fw, t_wl, t_fw) -> np.ndarray:
    """Source band as a rectangle, target as a Gaussian, integrated over the overlap.

    The formulation used by Spectral Python's ``BandResampler``.
    """
    s_lo, s_hi = s_wl - s_fw / 2.0, s_wl + s_fw / 2.0
    t_lo, t_hi = t_wl - t_fw / 2.0, t_wl + t_fw / 2.0
    lo = np.maximum(s_lo[None, :], t_lo[:, None])
    hi = np.minimum(s_hi[None, :], t_hi[:, None])
    sig = _sigma(t_fw)[:, None]
    w = _normal_cdf((hi - t_wl[:, None]) / sig) - _normal_cdf((lo - t_wl[:, None]) / sig)
    return np.where(hi > lo, w, 0.0)


def _weights_interp(s_wl, t_wl, kind: str) -> np.ndarray:
    """Interpolation expressed as a matrix, by interpolating the identity basis."""
    from scipy.interpolate import interp1d
    eye = np.eye(s_wl.size, dtype="float64")
    f = interp1d(s_wl, eye, kind=kind, axis=0, bounds_error=False, fill_value=np.nan)
    return np.asarray(f(t_wl))


def _weights_response(s_wl, s_fw, fine_wl, response) -> np.ndarray:
    """Measured target response against the source's own Gaussian bands."""
    fine = np.asarray(fine_wl, dtype="float64")
    R = np.asarray(response, dtype="float64")                       # (n_target, n_fine)
    sig = _sigma(s_fw)
    S = np.exp(-0.5 * ((fine[None, :] - s_wl[:, None]) / sig[:, None]) ** 2)   # (n_source, n_fine)
    S /= _trapz(S, fine, axis=1)[:, None]
    step = np.gradient(fine)
    return (R * step[None, :]) @ S.T                                # (n_target, n_source)


def resampling_matrix(source_wl, target_wl, source_fwhm=None, target_fwhm=None,
                      method: str = "gaussian", response=None, response_wl=None,
                      usable=None, min_coverage: float = 0.5,
                      allow_sharpening: bool = False) -> tuple:
    """The weights that turn source bands into target bands.

    Args:
        source_wl, target_wl: band centres, nm.
        source_fwhm, target_fwhm: band widths, nm. Inferred from the spacing by
            :func:`build_fwhm` when omitted, which is a guess, not a fact.
        method: one of :data:`METHODS`.
        response, response_wl: for ``method="response"``, the measured response
            ``(n_target, n_fine)`` on the grid ``response_wl``.
        usable: boolean mask of source bands to use. Unusable bands get zero
            weight and are excluded from the coverage.
        min_coverage: target bands covered less than this become NaN.
        allow_sharpening: permit a target narrower than the source.

    Returns:
        ``(matrix, coverage)``: ``(n_target, n_source)`` weights whose rows sum
        to 1, and the coverage fraction per target band. Rows below
        ``min_coverage`` are all NaN.

    Raises:
        ValueError: an unknown method, or a target finer than the source while
            ``allow_sharpening`` is False.
    """
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}; got {method!r}")
    s_wl = np.asarray(source_wl, dtype="float64")
    t_wl = np.asarray(target_wl, dtype="float64")
    s_fw = np.abs(np.asarray(source_fwhm, dtype="float64")) if source_fwhm is not None else build_fwhm(s_wl)
    if s_fw.size == 1:
        s_fw = np.full(s_wl.size, s_fw.item())
    if target_fwhm is None:
        t_fw = build_fwhm(t_wl) if t_wl.size > 1 else s_fw[np.argmin(np.abs(s_wl - t_wl[0]))][None]
    else:
        t_fw = np.abs(np.atleast_1d(np.asarray(target_fwhm, dtype="float64")))
        if t_fw.size == 1:
            t_fw = np.full(t_wl.size, t_fw.item())
    keep = np.ones(s_wl.size, bool) if usable is None else np.asarray(usable, bool)

    if not allow_sharpening:
        src_here = np.interp(t_wl, s_wl[keep], s_fw[keep])
        sharp = t_fw < src_here * 0.95
        if sharp.any():
            i = np.flatnonzero(sharp)
            raise ValueError(
                f"{sharp.sum()} target band(s) are narrower than the source: e.g. "
                f"{t_wl[i[0]]:.1f} nm asks for {t_fw[i[0]]:.2f} nm from a source that measures "
                f"{src_here[i[0]]:.2f} nm there. Resampling cannot raise spectral resolution; "
                "pass allow_sharpening=True to interpolate anyway."
            )

    if method == "gaussian":
        W = _weights_gaussian(s_wl, s_fw, t_wl, t_fw)
    elif method == "box":
        W = _weights_box(s_wl, s_fw, t_wl, t_fw)
    elif method == "response":
        if response is None or response_wl is None:
            raise ValueError("method='response' needs response= and response_wl=")
        W = _weights_response(s_wl, s_fw, response_wl, response)
    else:
        W = _weights_interp(s_wl, t_wl, {"linear": "linear", "cubic": "cubic",
                                         "nearest": "nearest"}[method])
    W = np.where(np.isfinite(W), W, 0.0)
    W[:, ~keep] = 0.0

    total = W.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        M = np.where(total[:, None] > 0, W / total[:, None], np.nan)

    cover = coverage_of(t_wl, t_fw, s_wl, s_fw, usable=keep)
    M[cover < min_coverage] = np.nan
    return M, cover


# --------------------------------------------------------------------------- #
# naming a target                                                              #
# --------------------------------------------------------------------------- #

def target_grid(source_wl=None, source_fwhm=None, *, step=None, fwhm=None, wl_range=None,
                wavelengths=None, like=None, sensor=None) -> dict:
    """Resolve the many ways of naming a target band set into one description.

    Exactly one of ``step``, ``wavelengths``, ``like`` or ``sensor`` is used.

    Returns:
        dict with ``wavelength``, ``fwhm``, ``label`` and, for an instrument
        with a measured response, ``response`` and ``response_wl``.
    """
    given = [n for n, v in (("step", step), ("wavelengths", wavelengths),
                            ("like", like), ("sensor", sensor)) if v is not None]
    if len(given) != 1:
        raise ValueError("give exactly one of step=, wavelengths=, like= or sensor=; "
                         f"got {given or 'none'}")

    if sensor is not None:
        from hyperproc.spectral import srf
        return srf.target(sensor)

    if like is not None:
        wl = np.asarray(like["wavelength"].values, dtype="float64")
        fw = (np.asarray(like["fwhm"].values, dtype="float64") if "fwhm" in like.coords
              else build_fwhm(wl))
        label = str(like.attrs.get("sensor", "") or "another dataset")
        return {"wavelength": wl, "fwhm": fw, "label": f"like {label}"}

    if wavelengths is not None:
        wl = np.atleast_1d(np.asarray(wavelengths, dtype="float64"))
        fw = (build_fwhm(wl) if fwhm is None else
              np.broadcast_to(np.atleast_1d(np.asarray(fwhm, dtype="float64")), wl.shape).copy())
        return {"wavelength": wl, "fwhm": fw, "label": f"{wl.size} given bands"}

    step = float(step)
    if step <= 0:
        raise ValueError("step must be positive")
    if wl_range is None:
        if source_wl is None:
            raise ValueError("step= needs wl_range= or a source to take the range from")
        s = np.asarray(source_wl, dtype="float64")
        wl_range = (float(np.ceil(s.min() / step) * step), float(np.floor(s.max() / step) * step))
    lo, hi = float(wl_range[0]), float(wl_range[1])
    wl = np.arange(lo, hi + step / 2.0, step)
    fw = (np.full(wl.size, step) if fwhm is None else
          np.broadcast_to(np.atleast_1d(np.asarray(fwhm, dtype="float64")), wl.shape).copy())
    return {"wavelength": wl, "fwhm": fw, "label": f"{step:g} nm grid, {fw[0]:g} nm bands"}


# --------------------------------------------------------------------------- #
# applying it                                                                  #
# --------------------------------------------------------------------------- #

def _apply_block(a: np.ndarray, M: np.ndarray, min_coverage: float = 0.5) -> np.ndarray:
    """Apply the resampling matrix, keeping a dead source band local.

    A dense product spreads a single NaN across the whole output, because
    ``0.0 * nan`` is ``nan``: one dead band at the end of the shortwave takes
    the visible with it. On the PRISMA test granule four unflagged bands near
    2490 nm carry NaN in some pixels, and that silently emptied the resampled
    spectrum of 31 % of them.

    So the gaps are zeroed and each target band is divided by the weight that
    actually landed on finite source bands. That is the renormalisation the
    static coverage test already performs, applied per pixel, and it is held
    to the same threshold: a target band that kept less than ``min_coverage``
    of its weight comes back NaN rather than as a confident-looking number
    built from a fraction of its response.
    """
    a = np.asarray(a, dtype="float32")
    Mt = np.asarray(M, dtype="float32").T
    finite = np.isfinite(a)
    if finite.all():
        return a @ Mt
    num = np.where(finite, a, np.float32(0.0)) @ Mt
    kept = finite.astype("float32") @ Mt          # weight that landed on real data
    # Divide only where weight was actually lost. A pixel that shares a block
    # with a dead neighbour but has none of its own keeps `num` untouched, so
    # it stays bit-identical to the plain product rather than picking up the
    # rounding of a division by a computed 1.0.
    out = num
    lost = kept < np.float32(1.0 - 1e-5)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(lost, num / kept, num)
    out[np.abs(kept) < min_coverage] = np.nan
    return out.astype("float32")


def resample(data, source_wl=None, source_fwhm=None, *, var=None, step=None, fwhm=None,
             wl_range=None, wavelengths=None, like=None, sensor=None,
             method: str | None = None, min_coverage: float = 0.5,
             allow_sharpening: bool = False, good_only: bool = True,
             return_coverage: bool = False, verbose: bool = False):
    """Resample a cube, a table of spectra or a single spectrum.

    Dispatches on **type**, never on shape: an ``xarray.Dataset`` goes through
    the metadata-aware path, anything array-like is treated as values whose
    last axis is wavelength, whatever the other axes mean.

    Args:
        data: a Dataset, or an array of any shape with wavelength last.
        source_wl, source_fwhm: required for arrays, read from a Dataset.
        var: which variable to resample; the main cube by default.
        step, fwhm, wl_range, wavelengths, like, sensor: how to name the
            target; see :func:`target_grid`.
        method: see :data:`METHODS`. None, the default, lets a ``sensor=``
            target use its own measured response and falls back to
            ``"gaussian"`` otherwise. An explicit choice always wins, which
            is how you compare a measured response against a Gaussian.
        min_coverage: target bands covered less than this become NaN.
        allow_sharpening: permit a target narrower than the source.
        good_only: drop bands flagged unusable by ``good_wavelength``.
        return_coverage: also return the per-target-band coverage.
        verbose: print what the target is and how well it is covered.

    Returns:
        The same kind that went in, with the new band set. For a Dataset the
        ``wavelength`` and ``fwhm`` coordinates are replaced, ``good_wavelength``
        becomes the coverage test, and ``attrs["spectral_resampling"]`` records
        what was done. Lazy input stays lazy.
    """
    if isinstance(data, xr.Dataset):
        return _resample_dataset(data, var=var, step=step, fwhm=fwhm, wl_range=wl_range,
                                 wavelengths=wavelengths, like=like, sensor=sensor,
                                 method=method, min_coverage=min_coverage,
                                 allow_sharpening=allow_sharpening, good_only=good_only,
                                 return_coverage=return_coverage, verbose=verbose)
    if source_wl is None:
        raise ValueError("resampling an array needs source_wl=")
    values = np.asarray(data, dtype="float64")
    s_wl = np.asarray(source_wl, dtype="float64")
    if values.shape[-1] != s_wl.size:
        raise ValueError(f"the last axis of the data is {values.shape[-1]} but source_wl has "
                         f"{s_wl.size} bands; wavelength must be the last axis")
    tgt = target_grid(s_wl, source_fwhm, step=step, fwhm=fwhm, wl_range=wl_range,
                      wavelengths=wavelengths, like=like, sensor=sensor)
    chosen = method or tgt.get("method") or "gaussian"
    M, cover = resampling_matrix(s_wl, tgt["wavelength"], source_fwhm, tgt["fwhm"],
                                 method=chosen,
                                 response=tgt.get("response"), response_wl=tgt.get("response_wl"),
                                 min_coverage=min_coverage, allow_sharpening=allow_sharpening)
    if verbose:
        print(f"resample -> {tgt['label']}: {len(cover)} bands, "
              f"{int(np.sum(cover >= min_coverage))} above {min_coverage:.0%} coverage"
              f", method {chosen}")
    out = _apply_block(values, np.nan_to_num(M, nan=0.0), min_coverage)
    out[..., cover < min_coverage] = np.nan
    return (out, cover) if return_coverage else out


def _resample_dataset(ds, *, var, step, fwhm, wl_range, wavelengths, like, sensor,
                      method, min_coverage, allow_sharpening, good_only, return_coverage, verbose):
    var = var or main_var(ds)
    s_wl = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    s_fw = (np.asarray(ds["fwhm"].values, dtype="float64") if "fwhm" in ds.coords
            else build_fwhm(s_wl))
    keep = good_bands(ds, good_only)
    tgt = target_grid(s_wl, s_fw, step=step, fwhm=fwhm, wl_range=wl_range,
                      wavelengths=wavelengths, like=like, sensor=sensor)
    chosen = method or tgt.get("method") or "gaussian"
    M, cover = resampling_matrix(s_wl, tgt["wavelength"], s_fw, tgt["fwhm"],
                                 method=chosen,
                                 response=tgt.get("response"), response_wl=tgt.get("response_wl"),
                                 usable=keep, min_coverage=min_coverage,
                                 allow_sharpening=allow_sharpening)
    ok = cover >= min_coverage
    if verbose:
        print(f"resample -> {tgt['label']}: {cover.size} bands, {int(ok.sum())} kept "
              f"(coverage >= {min_coverage:.0%}), method {chosen}")
        if (~ok).any():
            bad = tgt["wavelength"][~ok]
            print(f"  dropped: {', '.join(f'{w:.0f}' for w in bad[:8])}"
                  + (" ..." if bad.size > 8 else "") + " nm")

    da = ds[var]
    if da.dims[-1] != "wavelength":
        da = da.transpose(..., "wavelength")
    filled = np.nan_to_num(M, nan=0.0)
    res = xr.apply_ufunc(_apply_block, da, kwargs=dict(M=filled, min_coverage=min_coverage),
                         input_core_dims=[["wavelength"]], output_core_dims=[["new_wavelength"]],
                         dask="parallelized", output_dtypes=["float32"],
                         dask_gufunc_kwargs={"allow_rechunk": True,
                                             "output_sizes": {"new_wavelength": cover.size}})
    res = res.rename({"new_wavelength": "wavelength"})
    res = res.where(xr.DataArray(ok, dims=["wavelength"]))

    out = xr.Dataset(attrs=dict(ds.attrs))
    for name, v in ds.data_vars.items():
        if name != var and "wavelength" not in v.dims:
            out[name] = v
    out[var] = res.transpose(*[d if d != "wavelength" else "wavelength" for d in ds[var].dims])
    out[var].attrs = dict(ds[var].attrs)
    out = out.assign_coords(wavelength=("wavelength", tgt["wavelength"]),
                            fwhm=("wavelength", tgt["fwhm"]),
                            good_wavelength=("wavelength", ok),
                            band_coverage=("wavelength", cover))
    for c in ("x", "y"):
        if c in ds.coords:
            out = out.assign_coords({c: ds[c]})
    note = (f"{chosen} to {tgt['label']}; "
            f"{int(ok.sum())}/{cover.size} bands at coverage >= {min_coverage:.0%}")
    out[var].attrs["resampling"] = note
    out.attrs["spectral_resampling"] = note
    out["wavelength"].attrs.update(units="nm")
    out["band_coverage"].attrs.update(
        long_name="fraction of this band's response measured by the source", units="unitless")
    if "uncertainty" in ds:
        out.attrs["spectral_resampling"] += "; uncertainty dropped (resampling correlates bands)"
    return (out, cover) if return_coverage else out
