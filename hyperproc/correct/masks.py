"""Pixel masks the correction fits are drawn from.

A fit is only as good as its sample. Published correction workflows build
the sample from a few reusable pieces - an NDVI window, a
range on an ancillary layer, finiteness of the kernels, distance from the
swath edge - and the same pieces serve here. Each function returns a boolean
array that is True where a pixel is *usable*; :func:`combine` ANDs them.

:func:`zhai_cloud` is the spectral cloud/shadow test of Zhai et al. (2018),
written from the paper's equations, with the band choices (440, 550, 660,
850, 1570, 2110 nm) and the scene-adaptive thresholds the paper prescribes.
"""

from __future__ import annotations

import numpy as np


def ndi(band_a, band_b):
    """Normalised difference (a - b) / (a + b), NaN where undefined."""
    a = np.asarray(band_a, dtype="float64"); b = np.asarray(band_b, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (a - b) / (a + b)
    out[~np.isfinite(out)] = np.nan
    return out


def ndi_mask(band_a, band_b, lo=0.1, hi=1.0):
    """True where ``lo <= NDI(a, b) <= hi`` - e.g. NDVI from 850 and 660 nm."""
    v = ndi(band_a, band_b)
    return np.isfinite(v) & (v >= lo) & (v <= hi)


def range_mask(layer, lo=-np.inf, hi=np.inf):
    """True where a layer lies within ``[lo, hi]`` and is finite.

    ``np.radians(5)`` on a slope layer, ``0.12`` on cos i, ``np.radians(2)`` on
    the view zenith are the values EnSpec used for NEON.
    """
    x = np.asarray(layer, dtype="float64")
    return np.isfinite(x) & (x >= lo) & (x <= hi)


def kernel_finite(k_vol, k_geo):
    """True where both BRDF kernels are finite - guards grazing geometry."""
    return np.isfinite(k_vol) & np.isfinite(k_geo)


def edge_mask(valid, radius):
    """True for valid pixels at least ``radius`` pixels from the swath edge.

    Erodes the valid footprint: the outermost pixels
    of a flightline carry the strongest view-angle extremes and the most
    resampling artefacts, and the BRDF fit is better without them.
    """
    from scipy.ndimage import binary_erosion

    valid = np.asarray(valid, dtype=bool)
    if radius <= 0:
        return valid
    r = int(radius)
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    disk = (xx ** 2 + yy ** 2) <= r ** 2
    return binary_erosion(valid, structure=disk, border_value=0)


def combine(*masks):
    """AND together any number of boolean masks (None entries are skipped)."""
    out = None
    for m in masks:
        if m is None:
            continue
        out = np.asarray(m, dtype=bool) if out is None else (out & np.asarray(m, dtype=bool))
    if out is None:
        raise ValueError("combine() needs at least one mask")
    return out


def sample_indices(mask, fraction=0.1, max_samples=None, seed=0):
    """Random flat indices of True pixels - ``fraction`` of them, capped.

    The cap keeps a 20-line group from producing a hundred-million-row
    regression for no gain in the coefficients.
    """
    idx = np.flatnonzero(np.asarray(mask, dtype=bool))
    n = int(round(idx.size * fraction))
    if max_samples is not None:
        n = min(n, int(max_samples))
    if n >= idx.size:
        return idx
    return np.random.default_rng(seed).choice(idx, size=n, replace=False)


def _zhai_indices(blue, green, red, nir, swir1=None, swir2=None):
    blue, green, red, nir = (np.asarray(x, dtype="float64") for x in (blue, green, red, nir))
    with np.errstate(divide="ignore", invalid="ignore"):
        if swir1 is not None and swir2 is not None:
            swir1 = np.asarray(swir1, dtype="float64"); swir2 = np.asarray(swir2, dtype="float64")
            ci1 = (nir + 2.0 * swir1) / (blue + green + red)
            ci2 = (blue + green + red + nir + swir1 + swir2) / 6.0
            csi = (nir + swir1) / 2.0
        else:
            ci1 = 3.0 * nir / (blue + green + red)
            ci2 = (blue + green + red + nir) / 4.0
            csi = nir
    return blue, ci1, ci2, csi


def zhai_stats(blue, green, red, nir, swir1=None, swir2=None, valid=None):
    """The scene statistics Zhai's adaptive thresholds are built from.

    Returns a dict (``ci2_mean, ci2_max, csi_min, csi_mean, blue_min,
    blue_mean, n``) that :func:`zhai_cloud` accepts as ``stats`` so a mask
    computed block by block, or on a subsample, uses one scene-wide set of
    thresholds; the numbers also belong in a coefficient file's provenance.
    """
    blue, ci1, ci2, csi = _zhai_indices(blue, green, red, nir, swir1, swir2)
    ok = np.isfinite(ci2) & np.isfinite(csi) & np.isfinite(blue)
    if valid is not None:
        ok &= np.asarray(valid, dtype=bool)
    if not ok.any():
        return {"n": 0}
    return {"ci2_mean": float(ci2[ok].mean()), "ci2_max": float(ci2[ok].max()),
            "csi_min": float(csi[ok].min()), "csi_mean": float(csi[ok].mean()),
            "blue_min": float(blue[ok].min()), "blue_mean": float(blue[ok].mean()), "n": int(ok.sum())}


def zhai_thresholds(stats, t2=0.1, t3=0.25, t4=0.5):
    """T2, T3, T4 (paper eqs 5-7) from :func:`zhai_stats` output."""
    T2 = stats["ci2_mean"] + t2 * (stats["ci2_max"] - stats["ci2_mean"])
    T3 = stats["csi_min"] + t3 * (stats["csi_mean"] - stats["csi_min"])
    T4 = stats["blue_min"] + t4 * (stats["blue_mean"] - stats["blue_min"])
    return float(T2), float(T3), float(T4)


def zhai_cloud(blue, green, red, nir, swir1=None, swir2=None, valid=None,
               cloud=True, shadow=True, T1=0.01, t2=0.1, t3=0.25, t4=0.5,
               T7=9, T8=9, stats=None):
    """Cloud and cloud-shadow mask of Zhai et al. (2018), *ISPRS J. Photogramm.*
    144:235-253, without the spatial shadow refinement.

    Bands are reflectance arrays at roughly 440, 550, 660, 850 nm and, when the
    sensor reaches the SWIR, 1570 and 2110 nm. With SWIR (paper eqs 1a-b, 3):

        CI_1 = (NIR + 2 SWIR1) / (blue + green + red)
        CI_2 = (blue + green + red + NIR + SWIR1 + SWIR2) / 6
        CSI  = (NIR + SWIR1) / 2

    and without it ``CI_1 = 3 NIR / (blue + green + red)``,
    ``CI_2 = mean(blue, green, red, NIR)``, ``CSI = NIR``. The thresholds
    adapt to the scene (eqs 5-7), taken over ``valid`` pixels:

        T2 = mean(CI_2) + t2 (max(CI_2) - mean(CI_2))
        T3 = min(CSI)   + t3 (mean(CSI)  - min(CSI))
        T4 = min(blue)  + t4 (mean(blue) - min(blue))

    cloud  = |CI_1| < T1  or  CI_2 > T2,      then a T7 x T7 median filter
    shadow = CSI < T3  and  blue < T4,        then a T8 x T8 median filter

    ``stats`` (from :func:`zhai_stats`) fixes the scene statistics the
    thresholds are built from, so a mask evaluated block by block uses the
    same T2-T4 everywhere; without it they come from this call's ``valid``.

    Returns True where a pixel is cloud and/or shadow - i.e. the *bad* pixels,
    the opposite sense of the other masks here, so combine it as ``~zhai``.

    Two implementation choices matter more than they look, both checked on a
    NEON line (Sept 2026): (1) the tests are evaluated on ``valid`` pixels
    only - evaluating them on the fill value too makes every no-data pixel
    "shadow" and the median filter drags that flag T8/2 pixels into the
    swath; (2) the indices are computed in float64 - summing int16 x10000
    integers overflows on the brightest pixels, which on that line pulled
    max(CI_2) from 0.79 to 0.55 and T2 down with it, flagging 2.5x more
    pixels at t2 = 0.1.
    The paper's suggested ranges: T1 in {0.01, 0.1, 1, 10, 100}; t2 in
    1/10..1/2; t3 in 1/4..3/4; t4 in 1/2..5/6; T7, T8 odd in 3..11.

    On the CI_1 test: this function keeps the form of the reference
    implementation the package was validated against, ``|CI_1| < T1`` joined
    to the brightness test by OR. With the default ``T1 = 0.01`` that term
    practically never fires, so clouds are found by ``CI_2 > T2`` alone. An
    independent implementation of the same paper writes ``|CI_1 - 1| < T1``
    joined by AND (clouds have a flat spectrum, CI_1 near 1), and the paper's
    own experiments used T1 = 1, which is only meaningful for that reading. A
    deliberate decision (Sept 2026) kept the validated form; change both the
    centring and the conjunction together if that decision is revisited.
    """
    from scipy.ndimage import median_filter

    blue, ci1, ci2, csi = _zhai_indices(blue, green, red, nir, swir1, swir2)
    finite = np.isfinite(ci2) & np.isfinite(csi) & np.isfinite(blue)
    valid = finite if valid is None else (np.asarray(valid, dtype=bool) & finite)
    if not valid.any():
        return np.zeros(blue.shape, dtype=bool)
    if stats is None or stats.get("n", 0) == 0:
        stats = zhai_stats(blue, None, None, None, valid=valid) if False else {
            "ci2_mean": float(ci2[valid].mean()), "ci2_max": float(ci2[valid].max()),
            "csi_min": float(csi[valid].min()), "csi_mean": float(csi[valid].mean()),
            "blue_min": float(blue[valid].min()), "blue_mean": float(blue[valid].mean()), "n": int(valid.sum())}
    T2, T3, T4 = zhai_thresholds(stats, t2, t3, t4)

    out = np.zeros(blue.shape, dtype=bool)
    if cloud:
        clouds = valid & ((np.abs(ci1) < T1) | (ci2 > T2))
        out |= median_filter(clouds, size=int(T7))
    if shadow:
        shadows = valid & (csi < T3) & (blue < T4)
        out |= median_filter(shadows, size=int(T8))
    return out
