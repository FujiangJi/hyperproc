"""Spectral features: indices and absorption depths.

What separates these from :mod:`hyperproc.spectral` is what comes out. Those
transform a cube into a cube; these reduce each spectrum to one number per
pixel, so the result is a map.

Both halves address bands by **wavelength**, never by band number, which is
what lets one call run unchanged on EMIT at 285 bands, PACE at 122 and AVIRIS
at 425::

    import hyperproc as hp
    hp.spectral_index(ds, "NDVI")                          # a named index
    hp.spectral_index(ds, "(R800 - R670) / (R800 + R670)") # or write your own
    hp.band_depth(ds, "cellulose")
    print(hp.describe_indices(ds))              # which indices this sensor can compute

Fit these on the **unsmoothed** cube: :func:`hyperproc.smooth_spectra` is
cosmetic and correlates neighbouring bands, which biases exactly the narrow
features measured here.
"""
from __future__ import annotations

import ast
import re

import numpy as np
import xarray as xr

from hyperproc.io import main_var
from hyperproc.spectral.bands import TOLERANCE, band_at
from hyperproc.spectral.continuum import continuum_removal

__all__ = ["band_at", "index", "INDICES", "band_depth", "FEATURES", "describe_indices"]

#: Named indices, as formulas over wavelengths so they port across sensors.
INDICES: dict[str, dict] = {
    "NDVI":  {"formula": "(R860 - R660) / (R860 + R660)",
              "name": "normalised difference vegetation index", "reference": "Rouse et al. 1974"},
    "EVI":   {"formula": "2.5 * (R860 - R660) / (R860 + 6*R660 - 7.5*R480 + 1)",
              "name": "enhanced vegetation index", "reference": "Huete et al. 2002"},
    "NDWI":  {"formula": "(R860 - R1240) / (R860 + R1240)",
              "name": "normalised difference water index", "reference": "Gao 1996"},
    "NDII":  {"formula": "(R820 - R1650) / (R820 + R1650)",
              "name": "normalised difference infrared index", "reference": "Hunt and Rock 1989"},
    "PRI":   {"formula": "(R531 - R570) / (R531 + R570)",
              "name": "photochemical reflectance index", "reference": "Gamon et al. 1992"},
    "NDNI":  {"formula": "(log(1/R1510) - log(1/R1680)) / (log(1/R1510) + log(1/R1680))",
              "name": "normalised difference nitrogen index", "reference": "Serrano et al. 2002"},
    "CAI":   {"formula": "0.5 * (R2020 + R2220) - R2100",
              "name": "cellulose absorption index", "reference": "Nagler et al. 2003"},
    "MCARI": {"formula": "((R700 - R670) - 0.2 * (R700 - R550)) * (R700 / R670)",
              "name": "modified chlorophyll absorption ratio index", "reference": "Daughtry et al. 2000"},
    "ARI1":  {"formula": "1/R550 - 1/R700",
              "name": "anthocyanin reflectance index", "reference": "Gitelson et al. 2001"},
    "CRI1":  {"formula": "1/R510 - 1/R550",
              "name": "carotenoid reflectance index", "reference": "Gitelson et al. 2002"},
    "PSRI":  {"formula": "(R680 - R500) / R750",
              "name": "plant senescence reflectance index", "reference": "Merzlyak et al. 1999"},
    "NDSI":  {"formula": "(R550 - R1640) / (R550 + R1640)",
              "name": "normalised difference snow index", "reference": "Hall et al. 1995"},
}

#: Absorption features worth a depth, as the wavelength window to hull.
FEATURES: dict[str, tuple] = {
    "chlorophyll": (550.0, 750.0),
    "water_970": (900.0, 1050.0),
    "water_1200": (1100.0, 1300.0),
    "lignin_1730": (1650.0, 1850.0),
    "cellulose": (2000.0, 2300.0),
    "clay_2200": (2100.0, 2300.0),
}

_TOKEN = re.compile(r"\bR(\d+(?:\.\d+)?)\b")
_FUNCS = {"log": np.log, "log10": np.log10, "sqrt": np.sqrt, "exp": np.exp, "abs": np.abs}


# --------------------------------------------------------------------------- #
# indices                                                                      #
# --------------------------------------------------------------------------- #

def _evaluate(node, names: dict):
    """Evaluate a whitelisted arithmetic AST. No attribute access, no calls but _FUNCS."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, names)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"only numbers are allowed in a formula, got {node.value!r}")
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in names:
            raise ValueError(f"unknown name {node.id!r} in the formula; bands are written R<wavelength>")
        return names[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _evaluate(node.operand, names)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp):
        left, right = _evaluate(node.left, names), _evaluate(node.right, names)
        for kind, fn in ((ast.Add, lambda a, b: a + b), (ast.Sub, lambda a, b: a - b),
                         (ast.Mult, lambda a, b: a * b), (ast.Div, lambda a, b: a / b),
                         (ast.Pow, lambda a, b: a ** b)):
            if isinstance(node.op, kind):
                return fn(left, right)
        raise ValueError(f"operator {type(node.op).__name__} is not allowed in a formula")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ValueError(f"only {sorted(_FUNCS)} may be called in a formula")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed in a formula")
        return _FUNCS[node.func.id](*[_evaluate(a, names) for a in node.args])
    raise ValueError(f"{type(node).__name__} is not allowed in a formula")


def index(ds: xr.Dataset, formula: str, var: str | None = None, tolerance: float = TOLERANCE,
          good_only: bool = True, name: str | None = None) -> xr.DataArray:
    """Evaluate a spectral index written over wavelengths.

    Args:
        ds: dataset with a wavelength cube.
        formula: a name from :data:`INDICES` (``"NDVI"``) or an expression in
            which ``R<wavelength>`` means the band nearest that wavelength in
            nm, for example ``"(R800 - R670) / (R800 + R670)"``. Arithmetic,
            and the functions log, log10, sqrt, exp and abs, are allowed;
            nothing else is, so a formula from a paper is safe to paste.
        var: variable name; the main cube by default.
        tolerance: how far each band may sit from its requested wavelength.
        good_only: ignore bands flagged unusable.
        name: name for the result; the index name or ``"index"``.

    Returns:
        A lazy 2-D DataArray recording the formula and the wavelengths it
        actually used in ``attrs``.

    Raises:
        ValueError: the formula names no bands, uses something not allowed, or
            asks for a wavelength this sensor does not cover.
    """
    key = formula.strip().upper()
    meta = INDICES.get(key)
    expr = meta["formula"] if meta else formula
    name = name or (key if meta else "index")

    if not _TOKEN.search(expr):
        raise ValueError(f"the formula names no bands; write them as R<wavelength>, e.g. R860. Got: {expr!r}")
    bands, used = {}, {}
    for m in _TOKEN.finditer(expr):          # the token text is the variable name, kept verbatim
        token, wl = m.group(0), float(m.group(1))
        if token in bands:
            continue
        da = band_at(ds, wl, var=var, tolerance=tolerance, good_only=good_only)
        bands[token] = da
        used[token] = da.attrs["wavelength_used"]

    tree = ast.parse(expr, mode="eval")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = _evaluate(tree, bands)
    if not isinstance(out, xr.DataArray):
        raise ValueError("the formula produced a constant, not a map; it must reference at least one band")
    out = out.rename(name)
    out.attrs = {"long_name": (meta or {}).get("name", name), "formula": expr,
                 "bands_used": ", ".join(f"{k}={v}" for k, v in sorted(used.items())),
                 "units": "unitless"}
    if meta and meta.get("reference"):
        out.attrs["reference"] = meta["reference"]
    return out


def describe_indices(ds: xr.Dataset | None = None, tolerance: float = TOLERANCE) -> str:
    """The named indices, and which ones a given sensor can actually compute."""
    lines = [f"{'index':7s} {'status':10s} {'formula':58s} reference",
             f"{'-'*7} {'-'*10} {'-'*58} {'-'*24}"]
    for key, meta in INDICES.items():
        status = ""
        if ds is not None:
            try:
                index(ds, key, tolerance=tolerance)
                status = "available"
            except ValueError:
                status = "no bands"
        lines.append(f"{key:7s} {status:10s} {meta['formula']:58s} {meta['reference']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# absorption depth                                                             #
# --------------------------------------------------------------------------- #

def _argmin_wavelength(a: np.ndarray, wl: np.ndarray) -> np.ndarray:
    """Wavelength of the smallest value in each spectrum, NaN where all are missing."""
    filled = np.where(np.isfinite(a), a, np.inf)
    out = wl[np.argmin(filled, axis=-1)].astype("float32")
    return np.where(np.isfinite(a).any(axis=-1), out, np.nan).astype("float32")


def band_depth(ds: xr.Dataset, feature, var: str | None = None, good_only: bool = True) -> xr.Dataset:
    """Depth, position and area of an absorption feature.

    The continuum is the upper hull fitted inside the feature window, so the
    depth is measured against the shoulders rather than against an absolute
    reflectance, which is what makes it comparable between scenes.

    Args:
        ds: dataset with a wavelength cube.
        feature: a name from :data:`FEATURES` (``"cellulose"``) or a
            ``(lo, hi)`` window in nm.
        var: variable name; the main cube by default.
        good_only: fit only within runs of usable bands.

    Returns:
        A Dataset with ``depth`` (1 - the minimum of the continuum-removed
        spectrum), ``position`` (wavelength of that minimum, nm) and ``area``
        (integral of 1 - CR over the window, nm).
    """
    var = var or main_var(ds)
    if isinstance(feature, str) and feature not in FEATURES:
        raise ValueError(f"unknown feature {feature!r}; choose from {sorted(FEATURES)} or pass (lo, hi) nm")
    window = FEATURES[feature] if isinstance(feature, str) else tuple(feature)
    cr = continuum_removal(ds, var=var, window=window, good_only=good_only)[var]
    wl = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    inside = (wl >= window[0]) & (wl <= window[1])
    if inside.sum() < 3:
        raise ValueError(f"only {int(inside.sum())} bands inside {window[0]:g}-{window[1]:g} nm")
    sub = cr.isel(wavelength=np.flatnonzero(inside))
    depth = (1.0 - sub.min(dim="wavelength")).astype("float32")
    # The wavelength of the minimum is found inside the block rather than by indexing
    # with argmin: a chunked indexer cannot index a chunked array, so doing it the
    # obvious way works on a numpy cube and fails on every real, lazily read one.
    position = xr.apply_ufunc(_argmin_wavelength, sub, kwargs=dict(wl=wl[inside]),
                              input_core_dims=[["wavelength"]], dask="parallelized",
                              output_dtypes=["float32"])
    spacing = float(np.median(np.diff(wl[inside])))
    area = ((1.0 - sub).clip(min=0).sum(dim="wavelength") * spacing).astype("float32")

    out = xr.Dataset({"depth": depth, "position": position, "area": area},
                     attrs=dict(ds.attrs))
    label = feature if isinstance(feature, str) else f"{window[0]:g}-{window[1]:g} nm"
    out["depth"].attrs.update(long_name=f"{label} absorption depth", units="unitless")
    out["position"].attrs.update(long_name=f"{label} absorption minimum", units="nm")
    out["area"].attrs.update(long_name=f"{label} absorption area", units="nm")
    out.attrs.update(band_depth_feature=label, band_depth_window=f"{window[0]:g}-{window[1]:g} nm",
                     band_depth_bands=int(inside.sum()))
    return out
