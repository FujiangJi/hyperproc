"""Coregistration: measuring and removing the misalignment between two scenes.

Two products of the same ground rarely land on the same pixel. Geolocation
errors of one to two pixels are normal even in operational products, and they
are fatal to anything that compares scenes pixel by pixel: fusing a coarse
hyperspectral cube with a fine multispectral one, stacking dates into a time
series, or validating one sensor against another. Cropping both to a common
extent and trusting the headers, which is the usual shortcut, aligns the
corners and leaves the content offset.

    import hyperproc as hp
    fit = hp.estimate_shift(emit, planet)      # how far off, and how sure
    print(fit["report"])
    aligned = hp.coregister(emit, planet)      # same, then fixed

How it measures
---------------
Phase correlation between one band of each scene, resampled onto the
reference's grid. It uses the phase of the cross-power spectrum and not its
amplitude, so a brightness or calibration difference between two sensors does
not move the answer, which is what makes it usable across instruments. The
peak is refined by a parabolic fit to about a tenth of a pixel.

Whether to believe it
---------------------
A correlation peak always exists, even between unrelated images, so two
numbers come back with the shift. ``snr`` is the peak height against the rest
of the surface, and the scene is also split into tiles that are matched
independently: a real misregistration is the same in every tile, while a
spurious one scatters. ``consistent`` is False when the tiles disagree, and
that is the signal to look at the images rather than to apply the shift.

How it corrects
---------------
By default the georeferencing is moved and the pixels are left alone, which is
exact and costs nothing. ``resample=True`` puts the cube on the reference's
own grid instead, which is what pixel-to-pixel work needs, at the cost of one
interpolation.
"""
from __future__ import annotations

import warnings

import numpy as np
import xarray as xr

__all__ = ["estimate_shift", "tie_points", "apply_shift", "coregister", "DEFAULT_WAVELENGTH"]

#: Band used for matching unless told otherwise. The near infrared has strong,
#: sharp land-water and vegetation edges on almost every surface, and nearly
#: every imaging spectrometer covers it.
DEFAULT_WAVELENGTH = 860.0


def _grid_of(ds: xr.Dataset) -> tuple:
    """``(affine, crs, height, width)`` of a projected dataset."""
    from hyperproc.io import _transform_for
    crs = str(ds.attrs.get("crs", "") or "")
    if not crs:
        raise ValueError("coregistration needs projected datasets; this one has no CRS. "
                         "Put a swath on a grid first with hyperproc.georeference().")
    affine = _transform_for(ds)
    if affine is None:
        raise ValueError("cannot rebuild an affine transform from this dataset's coordinates")
    return affine, crs, ds.sizes["y"], ds.sizes["x"]


def _band_on(ds: xr.Dataset, wavelength: float, affine, crs, shape, var=None,
             tolerance: float = 60.0) -> np.ndarray:
    """One band of ``ds``, resampled onto the given grid."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    from hyperproc.io import main_var
    from hyperproc.spectral.bands import band_at

    var = var or main_var(ds)
    band = band_at(ds, wavelength, var=var, tolerance=tolerance)
    src_affine, src_crs, _, _ = _grid_of(ds)
    out = np.full(shape, np.nan, dtype="float32")
    reproject(np.asarray(band.values, dtype="float32"), out,
              src_transform=src_affine, src_crs=rasterio.crs.CRS.from_string(src_crs),
              dst_transform=affine, dst_crs=rasterio.crs.CRS.from_string(crs),
              src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.bilinear)
    return out


def _prepare(a: np.ndarray) -> np.ndarray:
    """Mean-removed, NaN-filled and windowed, ready for an FFT.

    The Hann window matters: an image is not periodic, and without it the
    discontinuity at the wrap-around produces a cross-shaped artefact through
    the correlation surface that can outrank the real peak.
    """
    a = np.asarray(a, dtype="float64")
    ok = np.isfinite(a)
    if ok.sum() < 16:
        return np.zeros_like(a)
    out = np.where(ok, a - a[ok].mean(), 0.0)
    ny, nx = out.shape
    out *= np.hanning(ny)[:, None] * np.hanning(nx)[None, :]
    return out


def _common_box(a: np.ndarray, b: np.ndarray) -> tuple:
    """Slices of the smallest box containing every pixel finite in both.

    Two scenes rarely cover exactly the same ground, and the part of the grid
    only one of them reaches is NaN. Filling that with zeros leaves a hard step
    in the middle of the array, and a step correlates with a step: the spurious
    peak can beat the real one outright. Cropping both to their common box
    removes it, and a crop applied equally to both cannot change the shift
    between them.
    """
    both = np.isfinite(a) & np.isfinite(b)
    if not both.any():
        return slice(0, 0), slice(0, 0)
    rows, cols = np.flatnonzero(both.any(axis=1)), np.flatnonzero(both.any(axis=0))
    return slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1)


def _phase_shift(moving: np.ndarray, reference: np.ndarray) -> tuple:
    """``(dy, dx, snr)``: how far ``moving`` must move to sit on ``reference``."""
    box = _common_box(moving, reference)
    moving, reference = moving[box], reference[box]
    if min(moving.shape) < 16:
        return np.nan, np.nan, 0.0
    a, b = _prepare(reference), _prepare(moving)
    if not a.any() or not b.any():
        return np.nan, np.nan, 0.0
    cross = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
    mag = np.abs(cross)
    surface = np.fft.ifft2(np.where(mag > 1e-12, cross / np.maximum(mag, 1e-12), 0)).real
    ny, nx = surface.shape
    peak = np.unravel_index(np.argmax(surface), surface.shape)

    # the peak height against the rest of the surface: an unrelated pair has none
    mask = np.ones_like(surface, dtype=bool)
    y0, y1 = max(0, peak[0] - 2), min(ny, peak[0] + 3)
    x0, x1 = max(0, peak[1] - 2), min(nx, peak[1] + 3)
    mask[y0:y1, x0:x1] = False
    background = surface[mask]
    rms = float(np.sqrt(np.mean(background ** 2))) if background.size else 0.0
    snr = float(surface[peak] / rms) if rms > 0 else 0.0

    # parabolic refinement, good to about a tenth of a pixel
    def _refine(axis_peak, values):
        left, right = values[(axis_peak - 1) % len(values)], values[(axis_peak + 1) % len(values)]
        centre = values[axis_peak]
        denom = left - 2 * centre + right
        return axis_peak + (0.0 if denom == 0 else 0.5 * (left - right) / denom)

    dy = _refine(peak[0], surface[:, peak[1]])
    dx = _refine(peak[1], surface[peak[0], :])
    if dy > ny / 2:
        dy -= ny
    if dx > nx / 2:
        dx -= nx
    return float(dy), float(dx), snr


def tie_points(moving: xr.Dataset, reference: xr.Dataset, wavelength: float = DEFAULT_WAVELENGTH,
               tiles: int = 4, min_snr: float = 3.0, min_finite: float = 0.25,
               var: str | None = None, ref_var: str | None = None) -> dict:
    """Match a grid of tiles independently, to see whether one shift describes the scene.

    Args:
        moving: the dataset to be aligned.
        reference: the dataset defining the grid and the truth.
        wavelength: band used for matching, nm.
        tiles: the scene is split ``tiles`` x ``tiles``.
        min_snr: tiles whose correlation peak is weaker than this are dropped.
        min_finite: tiles with less than this fraction of valid pixels are dropped.
        var, ref_var: variable names; the main cube of each by default.

    Returns:
        dict with per-tile ``dy``, ``dx``, ``snr``, their ``centre`` in pixels,
        and how many tiles were kept.
    """
    affine, crs, ny, nx = _grid_of(reference)
    a = _band_on(moving, wavelength, affine, crs, (ny, nx), var=var)
    from hyperproc.io import main_var
    b = np.asarray(reference[ref_var or main_var(reference)]
                   .isel(wavelength=_nearest_band(reference, wavelength, ref_var)).values, dtype="float32")

    out = {"dy": [], "dx": [], "snr": [], "centre": []}
    hy, hx = ny // tiles, nx // tiles
    if hy < 16 or hx < 16:
        raise ValueError(f"a {tiles}x{tiles} split of a {ny}x{nx} grid gives tiles of "
                         f"{hy}x{hx} pixels, too small to match; use fewer tiles")
    for i in range(tiles):
        for j in range(tiles):
            sl = (slice(i * hy, (i + 1) * hy), slice(j * hx, (j + 1) * hx))
            ta, tb = a[sl], b[sl]
            finite = min(np.isfinite(ta).mean(), np.isfinite(tb).mean())
            if finite < min_finite:
                continue
            dy, dx, snr = _phase_shift(ta, tb)
            if not np.isfinite(dy) or snr < min_snr:
                continue
            out["dy"].append(dy); out["dx"].append(dx); out["snr"].append(snr)
            out["centre"].append(((i + 0.5) * hy, (j + 0.5) * hx))
    for k in ("dy", "dx", "snr"):
        out[k] = np.array(out[k])
    out["kept"] = int(out["dy"].size)
    out["total"] = tiles * tiles
    return out


def _to_metres(dy_map: float, dx_map: float, crs: str, reference: xr.Dataset) -> tuple:
    """Map units to metres on the ground.

    A projected grid is already in metres; a geographic one is in degrees, and
    reporting "0.0 degrees" for a shift of three EMIT pixels tells nobody
    anything. Longitude shrinks by cos(latitude), so the scene's own latitude
    is used rather than a constant.
    """
    try:
        from pyproj import CRS
        if not CRS.from_user_input(crs).is_geographic:
            return dy_map, dx_map
    except Exception:
        return dy_map, dx_map
    lat = float(np.nanmean(np.asarray(reference["y"].values, dtype="float64"))) \
        if "y" in reference.coords else 0.0
    return dy_map * 111320.0, dx_map * 111320.0 * float(np.cos(np.radians(np.clip(lat, -89.9, 89.9))))


def _nearest_band(ds, wavelength, var=None) -> int:
    from hyperproc.io import main_var
    wl = np.asarray(ds[var or main_var(ds)]["wavelength"].values, dtype="float64")
    return int(np.argmin(np.abs(wl - wavelength)))


def estimate_shift(moving: xr.Dataset, reference: xr.Dataset,
                   wavelength: float = DEFAULT_WAVELENGTH, tiles: int = 4,
                   min_snr: float = 3.0, max_scatter: float = 1.0,
                   var: str | None = None, ref_var: str | None = None,
                   verbose: bool = False) -> dict:
    """How far ``moving`` sits from ``reference``, and whether to believe it.

    Args:
        moving, reference: projected datasets covering the same ground.
        wavelength: band used for matching, nm.
        tiles: tile grid for the consistency check; 0 skips it.
        min_snr: below this the whole-scene peak is not trusted.
        max_scatter: tiles must agree to within this many pixels (median
            absolute deviation) for the result to count as consistent.
        var, ref_var: variable names; the main cube of each by default.
        verbose: print the report as it is produced.

    Returns:
        dict with ``dy``/``dx`` in reference pixels, ``dy_m``/``dx_m`` in the
        reference's map units, ``snr``, ``scatter``, ``tiles_kept``,
        ``consistent`` and a human-readable ``report``.

    Raises:
        ValueError: the two do not overlap, or are not projected.
    """
    from hyperproc.io import main_var
    affine, crs, ny, nx = _grid_of(reference)
    a = _band_on(moving, wavelength, affine, crs, (ny, nx), var=var)
    if np.isfinite(a).mean() < 0.01:
        raise ValueError("the moving scene covers less than 1 % of the reference grid; "
                         "they do not appear to overlap")
    b = np.asarray(reference[ref_var or main_var(reference)]
                   .isel(wavelength=_nearest_band(reference, wavelength, ref_var)).values, dtype="float32")

    dy, dx, snr = _phase_shift(a, b)
    res_y, res_x = abs(affine.e), abs(affine.a)
    tp = {"kept": 0, "total": 0, "dy": np.array([]), "dx": np.array([])}
    scatter = np.nan
    if tiles and min(ny // tiles, nx // tiles) >= 16:
        tp = tie_points(moving, reference, wavelength, tiles=tiles, min_snr=min_snr,
                        var=var, ref_var=ref_var)
        if tp["kept"] >= 3:
            scatter = float(max(np.median(np.abs(tp["dy"] - np.median(tp["dy"]))),
                                np.median(np.abs(tp["dx"] - np.median(tp["dx"])))))

    consistent = bool(snr >= min_snr and (np.isnan(scatter) or scatter <= max_scatter))
    dy_metres, dx_metres = _to_metres(dy * res_y, dx * res_x, crs, reference)
    out = {"dy": dy, "dx": dx, "dy_m": dy * res_y, "dx_m": dx * res_x,
           "dy_metres": dy_metres, "dx_metres": dx_metres,
           "snr": snr, "scatter": scatter, "tiles_kept": tp["kept"], "tiles_total": tp["total"],
           "consistent": consistent, "wavelength": wavelength,
           "resolution": (res_y, res_x), "crs": crs}
    lines = [f"shift  {dy:+.2f} px down, {dx:+.2f} px right "
             f"({dy_metres:+.0f} m, {dx_metres:+.0f} m on the ground)",
             f"peak   snr {snr:.1f} (need {min_snr:g})"]
    if tp["total"]:
        lines.append(f"tiles  {tp['kept']}/{tp['total']} matched"
                     + (f", scatter {scatter:.2f} px (need <= {max_scatter:g})"
                        if np.isfinite(scatter) else ", too few to check consistency"))
    lines.append("verdict: " + ("consistent, safe to apply" if consistent else
                                "NOT consistent - look at the images before applying"))
    out["report"] = "\n".join(lines)
    if verbose:
        print(out["report"])
    return out


def apply_shift(ds: xr.Dataset, dy: float, dx: float, unit: str = "pixel") -> xr.Dataset:
    """Move a dataset's georeferencing by a shift, leaving the pixels untouched.

    Args:
        ds: the dataset to move.
        dy, dx: how far its content must move, down and right.
        unit: ``"pixel"`` of this dataset, or ``"map"`` units of its CRS.

    Returns:
        A copy with ``x``/``y`` coordinates and ``attrs["transform"]`` moved.
        Nothing is resampled, so this is exact and free.
    """
    from hyperproc.io import _transform_for
    affine = _transform_for(ds)
    if affine is None:
        raise ValueError("cannot rebuild an affine transform from this dataset's coordinates")
    if unit not in ("pixel", "map"):
        raise ValueError("unit must be 'pixel' or 'map'")
    res_y, res_x = abs(affine.e), abs(affine.a)
    off_x = dx * res_x if unit == "pixel" else dx
    off_y = dy * res_y if unit == "pixel" else dy
    # If the content at row r, column c belongs at row r+dy, column c+dx, then that pixel
    # is looking at the ground of the shifted position, so its coordinates take the shifted
    # position's values: x grows with dx, y shrinks with dy because y runs downwards.
    out = ds.copy()
    if "x" in out.coords:
        out = out.assign_coords(x=out["x"] + off_x)
    if "y" in out.coords:
        out = out.assign_coords(y=out["y"] - off_y)
    gt = [float(v) for v in ds.attrs.get("transform", ())]
    if len(gt) >= 6:
        gt[0] += off_x
        gt[3] -= off_y
        out.attrs["transform"] = tuple(gt)
    out.attrs["coregistration"] = (f"georeferencing moved by {dy:+.3f}, {dx:+.3f} "
                                   f"{'pixels' if unit == 'pixel' else 'map units'} "
                                   "(no resampling)")
    return out


def coregister(moving: xr.Dataset, reference: xr.Dataset, *, resample: bool = False,
               wavelength: float = DEFAULT_WAVELENGTH, tiles: int = 4, min_snr: float = 3.0,
               max_scatter: float = 1.0, force: bool = False, var: str | None = None,
               ref_var: str | None = None, verbose: bool = True) -> xr.Dataset:
    """Measure the misalignment against a reference and correct it.

    Args:
        moving, reference: projected datasets covering the same ground.
        resample: put the corrected cube on the reference's own grid. False,
            the default, only moves the georeferencing, which is exact.
        wavelength, tiles, min_snr, max_scatter, var, ref_var: see
            :func:`estimate_shift`.
        force: apply the shift even when the match is not consistent.
        verbose: print the report.

    Returns:
        The corrected dataset, carrying the measurement in
        ``attrs["coregistration"]``.

    Raises:
        ValueError: the match is not consistent and ``force`` is False.
    """
    fit = estimate_shift(moving, reference, wavelength=wavelength, tiles=tiles,
                         min_snr=min_snr, max_scatter=max_scatter, var=var, ref_var=ref_var,
                         verbose=verbose)
    if not fit["consistent"] and not force:
        raise ValueError(
            "the two scenes did not match consistently, so the shift is probably meaningless:\n"
            + fit["report"] + "\nPass force=True to apply it anyway, or try another wavelength.")

    res_y, res_x = fit["resolution"]
    _, moving_crs, _, _ = _grid_of(moving)
    m_affine = _grid_of(moving)[0]
    # the shift was measured in reference pixels; express it in the moving grid's own pixels
    out = apply_shift(moving, fit["dy_m"] / abs(m_affine.e), fit["dx_m"] / abs(m_affine.a))
    if resample:
        out = _to_reference_grid(out, reference, var=var)
    out.attrs["coregistration"] = (
        f"aligned to {reference.attrs.get('sensor', 'reference')} at {wavelength:g} nm: "
        f"{fit['dy']:+.2f}, {fit['dx']:+.2f} reference px "
        f"({fit['dy_metres']:+.0f}, {fit['dx_metres']:+.0f} m), snr {fit['snr']:.1f}, "
        f"{fit['tiles_kept']}/{fit['tiles_total']} tiles"
        + (f", scatter {fit['scatter']:.2f} px" if np.isfinite(fit["scatter"]) else "")
        + ("; resampled to the reference grid" if resample else "; georeferencing only"))
    return out


def _to_reference_grid(ds: xr.Dataset, reference: xr.Dataset, var=None) -> xr.Dataset:
    """Put every band of ``ds`` on the reference's grid, one band at a time."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    from hyperproc.io import main_var

    var = var or main_var(ds)
    affine, crs, ny, nx = _grid_of(reference)
    src_affine, src_crs, _, _ = _grid_of(ds)
    cube = ds[var]
    if cube.dims[-1] != "wavelength":
        cube = cube.transpose(..., "wavelength")
    # One band at a time: materialising the whole cube first would need 5 GB for a
    # full EMIT scene, and the readers hand it over lazily precisely to avoid that.
    nb = cube.sizes["wavelength"]
    out = np.full((ny, nx, nb), np.nan, dtype="float32")
    for k in range(nb):
        band = np.asarray(cube.isel(wavelength=k).values, dtype="float32")
        reproject(band, out[..., k],
                  src_transform=src_affine, src_crs=rasterio.crs.CRS.from_string(src_crs),
                  dst_transform=affine, dst_crs=rasterio.crs.CRS.from_string(crs),
                  src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.bilinear)
    new = xr.Dataset(attrs=dict(ds.attrs))
    new[var] = (("y", "x", "wavelength"), out)
    new[var].attrs = dict(ds[var].attrs)
    for c in ("wavelength", "fwhm", "good_wavelength", "band_index"):
        if c in ds.coords:
            new = new.assign_coords({c: ds[c]})
    new = new.assign_coords(x=reference["x"], y=reference["y"])
    new.attrs["crs"] = crs
    new.attrs["transform"] = tuple(affine.to_gdal())
    return new
