"""FlexBRDF: kernel-driven BRDF normalisation, stratified by NDVI.

From Queally et al. (2022), *FlexBRDF: A flexible BRDF correction for grouped
processing of airborne imaging spectroscopy flightlines*, JGR Biogeosciences,
The model per band and per NDVI class is the
Ross-Li linear kernel model of Lucht et al. (2000):

    rho(sza, vza, raa) = f_iso + f_vol K_vol(sza, vza, raa) + f_geo K_geo(sza, vza, raa)

and the correction is a multiplicative normalisation of each pixel to a
reference geometry - nadir view under a chosen solar zenith:

    rho_ref = rho * (f_iso + f_vol K_vol_ref + f_geo K_geo_ref)
                  / (f_iso + f_vol K_vol     + f_geo K_geo)

Three things make it "flex":

1. **NDVI stratification.** Coefficients are fitted separately for NDVI bins,
   because the anisotropy of bare soil, sparse and dense canopies differs.
   Bin edges are *dynamic* - percentiles of the pooled NDVI between
   ``perc_min`` and ``perc_max`` - so each bin holds a comparable number of
   pixels (:func:`dynamic_bins`).
2. **Grouped fitting.** The samples are pooled across every flightline in a
   group before fitting, so one coefficient set applies to all of them and
   seams between adjacent lines close. Grouping is the caller's job (the
   pipeline pools ``samples`` from many images); this module fits what it is
   given.
3. **Interpolation across bins.** At apply time the per-bin coefficients are
   interpolated linearly in NDVI (with extrapolation at the ends), so the
   correction is continuous rather than stepped at bin boundaries.

Scale invariance, worth knowing: the correction is a ratio of the same linear
model, so coefficients fitted on reflectance x 10 000 (as EnSpec's NEON
coefficient files were) apply unchanged to reflectance in 0-1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hyperproc.correct.kernels import kernel_pair, reference_kernels


# --- NDVI bins ----------------------------------------------------------------


def dynamic_bins(ndvi, num_bins=18, ndvi_min=0.05, ndvi_max=1.0,
                 perc_min=10, perc_max=95, second_split=True):
    """NDVI bin edges as percentiles of the pooled sample (Queally et al. 2022).

    ``num_bins - 1`` percentiles are taken evenly between ``perc_min`` and
    ``perc_max`` of the NDVI values above zero, then ``ndvi_min`` and
    ``ndvi_max`` are added as the outer edges. ``second_split`` additionally
    splits any bin wider than a threshold that shrinks with the bin count
    (``0.43125 - 0.015625 * (n - 1)``) at that bin's median, as the reference
    implementation of the method does.

    Returns:
        list of ``[lo, hi]`` pairs, ascending and contiguous.
    """
    v = np.asarray(ndvi, dtype="float64").ravel()
    v = v[np.isfinite(v) & (v > 0)]
    if v.size < 10:
        raise ValueError("too few NDVI samples to build bins")
    step = (perc_max - perc_min + 1) / (num_bins - 1)
    breaks = np.percentile(v, np.arange(perc_min, perc_max + 1, step)).tolist()
    edges = sorted(set([float(ndvi_min)] + breaks + [float(ndvi_max)]))
    if second_split:
        edges = _second_split(edges, v)
    return [[lo, hi] for lo, hi in zip(edges[:-1], edges[1:])]


def _second_split(edges, v):
    thresh = -0.015625 * (len(edges) - 1) + 0.43125
    widths = np.diff(edges)
    new = []
    for i in np.flatnonzero(widths >= thresh):
        inside = v[(v > edges[i]) & (v < edges[i + 1])]
        if inside.size:
            new.append(float(np.median(inside)))
    return sorted(edges + new)


def assign_bins(ndvi, bins):
    """Bin number 1..n per pixel (``ndvi`` in ``(lo, hi]``), 0 outside every bin."""
    v = np.asarray(ndvi, dtype="float64")
    out = np.zeros(v.shape, dtype=np.int16)
    for k, (lo, hi) in enumerate(bins, start=1):
        out[(v > lo) & (v <= hi)] = k
    return out


def bin_centres(bins):
    return np.array([(lo + hi) / 2.0 for lo, hi in bins])


# --- fitting ------------------------------------------------------------------


@dataclass
class FlexFit:
    """Fitted FlexBRDF coefficients for one group of images."""

    bins: list                      # [[lo, hi], ...]
    coeffs: np.ndarray              # (n_bands, n_bins, 3): f_vol, f_geo, f_iso
    volume: str
    geometric: str
    b_r: float
    h_b: float
    sza_ref: float                  # radians; the normalisation solar zenith
    n_per_bin: np.ndarray           # samples per bin
    r2: np.ndarray                  # (n_bands, n_bins) fit quality
    wavelength: np.ndarray | None = None
    meta: dict = field(default_factory=dict)

    def to_dict(self):
        """JSON-ready, wavelength-keyed where a wavelength axis is known."""
        d = {"type": "flex", "volume": self.volume, "geometric": self.geometric,
             "b/r": self.b_r, "h/b": self.h_b, "sza_ref_radians": float(self.sza_ref),
             "bins": {str(i): list(map(float, b)) for i, b in enumerate(self.bins, start=1)},
             "n_per_bin": self.n_per_bin.tolist(),
             "coeff_order": ["f_vol", "f_geo", "f_iso"], **self.meta}
        keys = ([f"{w:.4f}" for w in self.wavelength] if self.wavelength is not None
                else [str(i) for i in range(self.coeffs.shape[0])])
        d["coeffs"] = {k: self.coeffs[i].tolist() for i, k in enumerate(keys)}
        d["r2"] = {k: self.r2[i].tolist() for i, k in enumerate(keys)}
        return d

    @classmethod
    def from_dict(cls, d):
        """Inverse of :meth:`to_dict` (wavelength-keyed or index-keyed)."""
        keys = list(d["coeffs"])
        try:
            wl = np.array([float(k) for k in keys]); order = np.argsort(wl); wl = wl[order]
        except ValueError:                                   # index keys
            order = np.argsort([int(k) for k in keys]); wl = None
        keys = [keys[i] for i in order]
        bins = [list(map(float, d["bins"][k])) for k in sorted(d["bins"], key=int)]
        coeffs = np.array([[[np.nan if v is None else v for v in row] for row in d["coeffs"][k]] for k in keys], dtype=float)
        r2 = (np.array([[np.nan if v is None else v for v in d["r2"][k]] for k in keys], dtype=float)
              if "r2" in d else np.full(coeffs.shape[:2], np.nan))
        known = {"type", "volume", "geometric", "b/r", "h/b", "sza_ref_radians", "bins", "n_per_bin",
                 "coeff_order", "coeffs", "r2", "format", "version", "kind", "mode", "group",
                 "calc_mask", "apply_mask", "diversity", "source", "meta", "provenance"}
        return cls(bins=bins, coeffs=coeffs, volume=d["volume"], geometric=d["geometric"],
                   b_r=float(d["b/r"]), h_b=float(d["h/b"]), sza_ref=float(d["sza_ref_radians"]),
                   n_per_bin=np.asarray(d.get("n_per_bin", [-1] * len(bins))), r2=r2, wavelength=wl,
                   meta={k: v for k, v in d.items() if k not in known})


def fit_flex(rho, k_vol, k_geo, ndvi, bins, min_per_bin=30):
    """Fit f_vol, f_geo, f_iso per band and NDVI bin by least squares.

    Args:
        rho: ``(n_samples, n_bands)`` reflectance (any consistent scale).
        k_vol, k_geo: ``(n_samples,)`` kernels at each sample's geometry.
        ndvi: ``(n_samples,)`` used to assign bins.
        bins: from :func:`dynamic_bins` or user-specified ``[[lo, hi], ...]``.
        min_per_bin: bins with fewer samples get NaN coefficients (the apply
            step then falls back to interpolation from neighbours) rather
            than a fit through a handful of points.

    Returns:
        ``(coeffs (n_bands, n_bins, 3), n_per_bin, r2)``.
    """
    rho = np.asarray(rho, dtype="float64")
    if rho.ndim == 1:
        rho = rho[:, None]
    cls = assign_bins(ndvi, bins)
    X_all = np.column_stack([np.asarray(k_vol, float), np.asarray(k_geo, float),
                             np.ones(len(cls))])
    nb, nbin = rho.shape[1], len(bins)
    coeffs = np.full((nb, nbin, 3), np.nan)
    r2 = np.full((nb, nbin), np.nan)
    n_per = np.zeros(nbin, dtype=int)
    for j in range(nbin):
        sel = cls == j + 1
        n_per[j] = int(sel.sum())
        if n_per[j] < min_per_bin:
            continue
        X = X_all[sel]
        Y = rho[sel]
        ok = np.isfinite(Y).all(axis=1) & np.isfinite(X).all(axis=1)
        if ok.sum() < min_per_bin:
            continue
        beta, *_ = np.linalg.lstsq(X[ok], Y[ok], rcond=None)     # (3, n_bands)
        coeffs[:, j, :] = beta.T
        pred = X[ok] @ beta
        ss_res = ((Y[ok] - pred) ** 2).sum(axis=0)
        ss_tot = ((Y[ok] - Y[ok].mean(axis=0)) ** 2).sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            r2[:, j] = 1.0 - ss_res / ss_tot
    return coeffs, n_per, r2


# --- applying -----------------------------------------------------------------


def interpolate_coeffs(coeffs, bins, ndvi):
    """Per-pixel ``(f_vol, f_geo, f_iso)`` by linear interpolation in NDVI.

    Interpolates each band's coefficients between bin centres, extrapolating
    linearly beyond the outer centres. Bins with NaN coefficients are skipped, so a
    sparse bin borrows from its neighbours.

    Returns:
        ``(n_bands, 3, *ndvi.shape)`` array.
    """
    centres = bin_centres(bins)
    v = np.asarray(ndvi, dtype="float64")
    nb = coeffs.shape[0]
    out = np.full((nb, 3) + v.shape, np.nan)
    flat = v.ravel()
    for b in range(nb):
        for c in range(3):
            y = coeffs[b, :, c]
            ok = np.isfinite(y)
            if ok.sum() == 0:
                continue
            if ok.sum() == 1:
                out[b, c] = y[ok][0]
                continue
            xs, ys = centres[ok], y[ok]
            f = np.interp(flat, xs, ys)
            # linear extrapolation beyond the outer centres
            lo, hi = flat < xs[0], flat > xs[-1]
            if lo.any():
                s = (ys[1] - ys[0]) / (xs[1] - xs[0]); f[lo] = ys[0] + s * (flat[lo] - xs[0])
            if hi.any():
                s = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]); f[hi] = ys[-1] + s * (flat[hi] - xs[-1])
            out[b, c] = f.reshape(v.shape)
    return out


def apply_flex(rho, k_vol, k_geo, ndvi, fit: FlexFit, mask=None, slab=48, ratio_max=5.0):
    """Normalise ``rho (..., band)`` to nadir view at ``fit.sza_ref``.

    Pixels where ``mask`` is False, NDVI is outside every bin, or the modelled
    observed reflectance is not positive are returned unchanged - the last
    because a non-positive denominator means the model does not describe that
    pixel and a ratio would be nonsense. The same goes for a ratio outside
    ``[1/ratio_max, ratio_max]``: a kernel model fitted on a bin describes the
    bin's average anisotropy, and a factor of 5 or more only arises where the
    modelled reflectance sits at the noise floor (seen at 427-479 nm in a
    high-NDVI bin, where -0.0009 became -0.064 without the bound). Such a
    pixel/band is left as it is rather than amplified. Bands are processed
    ``slab`` at a time so the per-pixel interpolated coefficients never
    exceed a few hundred MB for a full-swath block.
    """
    rho = np.asarray(rho, dtype="float32")
    nb = rho.shape[-1]
    kv_ref, kg_ref = reference_kernels(fit.sza_ref, fit.volume, fit.geometric, fit.b_r, fit.h_b)
    kv = np.asarray(k_vol, dtype="float64"); kg = np.asarray(k_geo, dtype="float64")
    inside = assign_bins(ndvi, fit.bins) > 0
    if mask is not None:
        inside &= np.asarray(mask, dtype=bool)
    out = np.array(rho, dtype="float32", copy=True)
    for b0 in range(0, nb, max(1, int(slab))):
        b1 = min(nb, b0 + max(1, int(slab)))
        f = interpolate_coeffs(fit.coeffs[b0:b1], fit.bins, ndvi)          # (s, 3, ...)
        f_vol, f_geo, f_iso = f[:, 0], f[:, 1], f[:, 2]                    # each (s, ...)
        modelled = f_iso + f_vol * kv[None] + f_geo * kg[None]              # (s, ...)
        target = f_iso + f_vol * kv_ref + f_geo * kg_ref
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = target / modelled
        keep = np.isfinite(ratio) & (modelled > 0) & inside[None]
        if ratio_max is not None:
            keep &= (ratio > 1.0 / ratio_max) & (ratio < ratio_max)
        ratio = np.moveaxis(np.where(keep, ratio, 1.0), 0, -1)              # (..., s)
        out[..., b0:b1] = (rho[..., b0:b1] * ratio).astype("float32")
    return out


def fit_group(rho, sza, vza, raa, ndvi, wavelength=None, volume="ross_thick",
              geometric="li_dense_r", b_r=1.0, h_b=2.0, sza_ref=None,
              bins=None, bin_ndvi=None, **bin_kwargs):
    """Fit a :class:`FlexFit` from pooled samples of one or many images.

    ``sza_ref`` defaults to the mean solar zenith of the samples, which for a
    group is the group mean.

    ``bin_ndvi`` is the population the dynamic bin edges are cut from when
    ``bins`` is not given. FlexBRDF cuts them from the NDVI of *every* valid
    pixel of every image in the group, and only then restricts the fit to the
    masked, subsampled pixels; passing the fit sample instead (the default
    when ``bin_ndvi`` is None) shifts the edges upward because the vegetation
    mask has already removed the low-NDVI tail.
    """
    sza = np.asarray(sza, float); vza = np.asarray(vza, float); raa = np.asarray(raa, float)
    k_vol, k_geo = kernel_pair(sza, vza, raa, volume, geometric, b_r, h_b)
    if bins is None:
        bins = dynamic_bins(ndvi if bin_ndvi is None else bin_ndvi, **bin_kwargs)
    coeffs, n_per, r2 = fit_flex(rho, k_vol, k_geo, ndvi, bins)
    return FlexFit(bins=bins, coeffs=coeffs, volume=volume, geometric=geometric,
                   b_r=b_r, h_b=h_b,
                   sza_ref=float(np.nanmean(sza) if sza_ref is None else sza_ref),
                   n_per_bin=n_per, r2=r2,
                   wavelength=None if wavelength is None else np.asarray(wavelength, float))
