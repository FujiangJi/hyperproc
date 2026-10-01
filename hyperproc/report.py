"""Human-readable summary of any cube a reader returns."""

from __future__ import annotations

import numpy as np
import xarray as xr

_FLAGS = ("cloud", "cirrus", "water", "spacecraft", "dilated_cloud", "snow", "shadow")
_ANGLES = ("sza", "saa", "vza", "vaa", "raa")

#: Read at most this many cube elements when summarising. An AVIRIS flightline
#: is 10-30 GB and lazy, so pulling all of it to print a median is not an
#: option; a strided sample gives the same picture for the cost of a few reads.
_SAMPLE = 2_000_000


def _thin(da, target: int = _SAMPLE):
    """Read about ``target`` elements out of a cube. Returns (array, sampled).

    Striding is the obvious way to do this and the wrong one: an AVIRIS cube is
    chunked along ``y``, so ``[::40]`` touches every chunk and pulls all 11 GB
    to print a median. Reading a few small blocks costs a handful of chunk
    reads instead, and still samples the length of the flightline rather than
    one corner of it.

    The blocks are square-ish rather than whole rows because the two layouts
    punish opposite things. ENVI BIL reads a full image line either way, so
    narrowing ``x`` is free. AVIRIS-5's NetCDF is gzipped in ``(10, 256, 256)``
    chunks, where one full row across 424 bands means decompressing 1.7 GB -
    17 s for a single row, against a few for a whole block.
    """
    n = int(np.prod(da.shape))
    if n <= target or "y" not in da.dims or "x" not in da.dims:
        return np.asarray(da.values), n > target
    dims = list(da.dims)
    ny, nx = da.sizes["y"], da.sizes["x"]
    per_px = max(1, n // (ny * nx))          # elements behind each pixel (bands)
    grid = 3                                 # a 3x3 lattice of blocks
    side = max(1, int(np.sqrt(target / (grid * grid * per_px))))
    hy, hx = min(side, ny), min(side, nx)
    # A lattice, not a diagonal: on a rotated grid the diagonal runs down the
    # middle of the swath and would report every scene as 100% valid, while the
    # corners that are actually off-swath fill never get looked at. Interior
    # positions, because the outermost row and column are nearly all fill.
    ys = np.linspace(0, max(0, ny - hy), grid + 2)[1:-1].astype(int)
    xs = np.linspace(0, max(0, nx - hx), grid + 2)[1:-1].astype(int)
    parts = [np.asarray(da.isel(y=slice(int(y), int(y) + hy),
                                x=slice(int(x), int(x) + hx)).values)
             for y in ys for x in xs]
    return np.concatenate(parts, axis=dims.index("y")), True


def describe(ds: xr.Dataset, var: str = "reflectance") -> None:
    """Print shape, extent, wavelengths, data range, masks and geometry."""
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    wl = ds["wavelength"].values
    if var not in ds:
        var = "radiance" if "radiance" in ds else next(iter(ds.data_vars))
    r, sampled = _thin(ds[var])
    finite = np.isfinite(r)

    print(f"\n  sensor     {ds.attrs.get('sensor', '?')} {ds.attrs.get('level', '')}")
    print(f"  granule    {ds.attrs.get('granule', '?')}")
    if ds.attrs.get("datetime"):
        print(f"  acquired   {ds.attrs['datetime']}")
    grid = "ortho" if ds.attrs.get("orthorectified") else "sensor"
    print(f"  grid       {ny} x {nx}  ({grid})")

    if "transform" in ds.attrs:
        gt = ds.attrs["transform"]
        # hypot, not gt[1]: a rotated grid (AVIRIS) splits the pixel size
        # across the scale and shear terms, so gt[1] alone understates it.
        size = float(np.hypot(gt[1], gt[4]))
        deg = size < 1e-2  # geographic CRS
        px = f"{size * 111320:.0f} m" if deg else f"{size:.1f} m"
        rot = ds.attrs.get("rotation_deg")
        print(f"  pixel      {px}" + (f"   (grid rotated {rot:g} deg)" if rot else ""))
        # Bounding box from the affine, not from the 1-D x/y coordinates: on a
        # flight-aligned grid those describe only the top row and left column
        # (5 km short for AVIRIS-3, 139 km for a Classic line).
        from hyperproc.io import _transform_for
        aff = _transform_for(ds)
        if aff is not None:
            cs = [(aff.c + aff.a * c + aff.b * r, aff.f + aff.d * c + aff.e * r)
                  for c, r in ((0, 0), (nx, 0), (0, ny), (nx, ny))]
            xs, ys = [p[0] for p in cs], [p[1] for p in cs]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        else:
            x0, x1 = float(ds.x.min()), float(ds.x.max())
            y0, y1 = float(ds.y.min()), float(ds.y.max())
        print(f"  extent     x {x0:.4f} .. {x1:.4f}   y {y0:.4f} .. {y1:.4f}"
              + ("   (bounding box of the rotated grid)" if rot else ""))

    print(f"  bands      {wl.size}   {wl[0]:.1f} - {wl[-1]:.1f} nm", end="")
    if "fwhm" in ds.coords:
        print(f"   (fwhm {float(ds.fwhm.mean()):.1f} nm)")
    else:
        print()
    if "good_wavelength" in ds.coords:
        n_bad = int((~ds["good_wavelength"].values).sum())
        if n_bad:
            # Whose judgement this is matters: AVIRIS-3 ships a bbl, but for
            # most AVIRIS products the flag is derived from the water-vapour
            # windows, which is our inference, not the provider's.
            src = ds.attrs.get("good_bands_source", "provider")
            whose = ("marked unusable by the provider" if "bbl" in src
                     else f"flagged unusable ({src})")
            print(f"  flagged    {n_bad} bands {whose}")

    note = f"   (from a {finite[..., 0].size:,}-px sample)" if sampled else ""
    print(f"  valid px   {"~" if sampled else ""}{100 * finite[..., 0].mean():.1f}% of {ny * nx:,}{note}")
    if finite.any():
        v = r[finite]
        print(f"  {var[:9]:<9}  median {np.median(v):.4f}   p1 {np.percentile(v, 1):.4f}"
              f"   p99 {np.percentile(v, 99):.4f}")

    flags = [k for k in _FLAGS if k in ds]
    if flags:
        print("  masks     ", "  ".join(
            f"{k}={100 * _thin(ds[k])[0].mean():.1f}%" for k in flags))
    angles = [k for k in _ANGLES if k in ds]
    if angles:
        print("  geometry  ", "  ".join(
            f"{k}={np.nanmean(_thin(ds[k])[0]):.1f}deg" for k in angles))
    terrain = [k for k in ("slope", "aspect", "cos_i") if k in ds]
    if terrain:
        print("  terrain   ", "  ".join(
            f"{k}={np.nanmedian(_thin(ds[k])[0]):.2f}" for k in terrain)
            + ("   " + ds.attrs["geometry_fixed"] if "geometry_fixed" in ds.attrs else ""))
    print()
