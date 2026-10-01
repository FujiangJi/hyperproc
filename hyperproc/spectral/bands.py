"""Addressing bands by wavelength, and the runs of usable bands.

Everything spectral in this package is addressed by **wavelength**, never by
band number. That is the difference between an operation that ports across
sensors and one that quietly moves when the instrument changes: ``R860`` means
the band nearest 860 nm on whatever is in hand, and asking for a wavelength a
sensor does not cover fails loudly rather than returning the wrong band.

:func:`runs_of_good_bands` is the other half. A hyperspectral spectrum is not
one continuous signal: the water-vapour regions are unusable, and a filter, a
hull or a derivative that reaches across such a gap measures the gap. Every
function in this subpackage works inside the runs this returns.
"""
from __future__ import annotations

import numpy as np
import xarray as xr

from hyperproc.io import main_var

__all__ = ["TOLERANCE", "band_at", "runs_of_good_bands", "good_bands"]

#: Default distance, in nm, a requested wavelength may sit from the nearest band.
TOLERANCE = 20.0


def good_bands(ds: xr.Dataset, good_only: bool = True) -> np.ndarray:
    """Boolean mask of usable bands, all True when the dataset flags none."""
    n = ds.sizes["wavelength"]
    if good_only and "good_wavelength" in ds.coords:
        flagged = np.asarray(ds["good_wavelength"].values, dtype=bool)
        if flagged.any():
            return flagged
    return np.ones(n, bool)


def runs_of_good_bands(good: np.ndarray, min_len: int) -> list:
    """Index ranges of consecutive usable bands at least ``min_len`` long."""
    out, start = [], None
    for i, ok in enumerate(list(good) + [False]):
        if ok and start is None:
            start = i
        elif not ok and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    return out


#: Kept as a private alias: the name used before the subpackage split.
_runs = runs_of_good_bands


def band_at(ds: xr.Dataset, wavelength: float, var: str | None = None,
            tolerance: float = TOLERANCE, good_only: bool = True) -> xr.DataArray:
    """The band nearest ``wavelength`` nm.

    Args:
        ds: dataset with a wavelength cube.
        wavelength: what to look for, nm.
        var: variable name; the main cube by default.
        tolerance: how far the nearest band may sit from the request.
        good_only: ignore bands flagged unusable by ``good_wavelength``.
            Falls back to all bands, with a warning, if that leaves nothing.

    Returns:
        The 2-D slice, with ``wavelength_requested`` and the band's own
        wavelength in its attrs.

    Raises:
        ValueError: nothing lies within ``tolerance``. The message says what
            was asked for and what the nearest band actually is, because on a
            VNIR-only sensor that is the whole story.
    """
    var = var or main_var(ds)
    wls = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    usable = np.ones(wls.size, bool)
    if good_only and "good_wavelength" in ds.coords:
        flagged = np.asarray(ds["good_wavelength"].values, dtype=bool)
        if flagged.any():
            usable = flagged
    cand = np.flatnonzero(usable)
    i = int(cand[np.argmin(np.abs(wls[cand] - wavelength))])
    if abs(wls[i] - wavelength) > tolerance:
        raise ValueError(
            f"no usable band within {tolerance:g} nm of {wavelength:g} nm; the nearest is "
            f"{wls[i]:.1f} nm ({abs(wls[i] - wavelength):.1f} nm away). This sensor covers "
            f"{wls[usable].min():.0f}-{wls[usable].max():.0f} nm."
        )
    out = ds[var].isel(wavelength=i)
    out.attrs.update(ds[var].attrs)
    out.attrs.update(wavelength_requested=f"{wavelength:g} nm", wavelength_used=f"{wls[i]:.2f} nm",
                     band_index=int(i))
    return out
