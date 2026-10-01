"""One quality layer for every sensor, as documented bit flags.

Each provider ships its own masks under its own names and its own polarity.
Nine spellings mean "cloud" across the readers in this package
(``cloud``, ``dilated_cloud``, ``cloud_land``, ``cloud_water``, ``cldice``,
and the cirrus variants); shadow is ``shadow`` on DESIS and ``cloudshadow`` on
EnMAP; ``valid`` is true when a pixel is good while ``nodata`` is true when it
is not; and the AVIRIS family ships nothing at all. Anyone who did not build
the pipeline has to learn all of that before they can mask a cube.

This module reduces it to one ``uint16`` layer with one bit per condition,
the way Landsat's ``QA_PIXEL`` does::

    import hyperproc as hp
    q = hp.quality_flags(ds)                # uint16 (y, x)
    hp.quality_summary(q)                   # {'cloud': 0.11, 'water': 0.38, ...}
    clear = hp.quality_apply(ds, q)         # cube set to NaN where cloudy or fill
    print(hp.quality_table(q))              # the bit table with per-flag shares

The per-sensor layers are left exactly as the readers produce them, so nothing
that already reads ``ds["cloud"]`` breaks; this is an additional view of them.

The bits
--------
=====  ====================  ===============================================
Bit    Flag                  Set when
=====  ====================  ===============================================
0      fill                  no observation (off-swath, nodata, nav failure)
1      saturated             a band is at the detector rail
2      cloud                 opaque cloud
3      cloud_shadow          shadow cast by cloud
4      cirrus                thin or high cloud
5      snow_ice              snow or ice
6      water                 inland or ocean water
7      haze                  aerosol haze flagged by the provider
8      sun_glint             specular reflection geometry
9      terrain_shadow        not illuminated by the direct beam (cos i <= 0)
10     steep_terrain         slope beyond what a topographic correction holds
11     ac_failed             atmospheric correction did not converge
12     brdf_filled           BRDF c-factor not taken from MODIS
13     negative_reflectance  many good bands below zero after correction
=====  ====================  ===============================================

Bits 14 and 15 are reserved. Stages add their own bits as they run:
:func:`hyperproc.correct.nbar` records ``brdf_filled`` through ``brdf_valid``,
and :func:`hyperproc.atmos.process` writes the layer beside every product.
"""
from __future__ import annotations

import warnings

import numpy as np
import xarray as xr

__all__ = ["FLAGS", "FLAG_DESCRIPTIONS", "BOOLEAN_SOURCES", "CODED_SOURCES", "DEFAULT_DROP",
           "build", "decode", "summary", "apply", "set_flag", "describe"]

#: Flag name -> bit number. The order is fixed: changing it invalidates written products.
FLAGS: dict[str, int] = {
    "fill": 0, "saturated": 1, "cloud": 2, "cloud_shadow": 3, "cirrus": 4,
    "snow_ice": 5, "water": 6, "haze": 7, "sun_glint": 8, "terrain_shadow": 9,
    "steep_terrain": 10, "ac_failed": 11, "brdf_filled": 12, "negative_reflectance": 13,
}

FLAG_DESCRIPTIONS: dict[str, str] = {
    "fill": "no observation (off-swath, nodata, navigation failure)",
    "saturated": "a band is at the detector rail",
    "cloud": "opaque cloud",
    "cloud_shadow": "shadow cast by cloud",
    "cirrus": "thin or high cloud",
    "snow_ice": "snow or ice",
    "water": "inland or ocean water",
    "haze": "aerosol haze flagged by the provider",
    "sun_glint": "specular reflection geometry",
    "terrain_shadow": "not illuminated by the direct beam (cos i <= 0)",
    "steep_terrain": "slope beyond what a topographic correction holds",
    "ac_failed": "atmospheric correction did not converge",
    "brdf_filled": "BRDF c-factor not taken from MODIS at this pixel",
    "negative_reflectance": "many good bands below zero after correction",
}

#: What to mask by default: the pixels almost no analysis wants.
DEFAULT_DROP = ("fill", "cloud", "cloud_shadow", "cirrus")

#: Boolean reader layers -> (flag, the value that sets it). ``False`` inverts,
#: which is how ``valid`` and ``land`` are folded in without a special case.
BOOLEAN_SOURCES: dict[str, tuple[str, bool]] = {
    # cloud, in its many spellings
    "cloud": ("cloud", True), "dilated_cloud": ("cloud", True),
    "cloud_land": ("cloud", True), "cloud_water": ("cloud", True), "cldice": ("cloud", True),
    "cirrus": ("cirrus", True),
    # shadow
    "shadow": ("cloud_shadow", True), "cloudshadow": ("cloud_shadow", True),
    # surface type. A "land" layer is deliberately NOT inverted into water: on the
    # DESIS scene here, 10.8 % of the observed pixels are flagged water but 20.6 %
    # are flagged not-land, so the two are not complements and inverting one would
    # invent water over the 9.8 % that is neither. Both sensors that ship "land"
    # (DESIS, PACE) ship "water" as well, so nothing is lost.
    "snow": ("snow_ice", True), "water": ("water", True),
    # atmosphere and geometry
    "haze": ("haze", True), "haze_land": ("haze", True), "haze_water": ("haze", True),
    "sunglint": ("sun_glint", True), "higlint": ("sun_glint", True),
    # instrument and processing
    "hilt": ("saturated", True), "l1_sat_err": ("saturated", True),
    "atmfail": ("ac_failed", True),
    # no observation. EMIT's spacecraft flag marks pixels the platform itself
    # contaminated, which is not a measurement either.
    "navfail": ("fill", True), "spacecraft": ("fill", True),
    "nodata": ("fill", True), "valid": ("fill", False),
}

#: Coded integer layers -> {flag: the codes that set it}.
CODED_SOURCES: dict[str, dict[str, tuple]] = {
    # PRISMA L1, ASI's own table (0 water, 1 snow, 2 bare, 3 crops, 4 forest, 5 wetland, 6 urban)
    "landcover": {"water": (0,), "snow_ice": (1,)},
    # written by hyperproc.correct.nbar: 0 filled, 1 retrieved, 2 outside the observation
    "brdf_valid": {"brdf_filled": (0,), "fill": (2,)},
    # NEON / ATCOR "Haze, Cloud, Water" map, 23 classes
    "hcw_class": {
        "fill": (0,), "cloud_shadow": (1, 22), "cirrus": (2, 3, 4, 8, 9, 10, 18, 19),
        "saturated": (6,), "snow_ice": (7,), "haze": (11, 12, 13, 14),
        "sun_glint": (13, 14), "cloud": (15, 16), "water": (17,), "terrain_shadow": (21,),
    },
    # NEON / ATCOR dark-dense-vegetation map
    "ddv_class": {"fill": (0,), "water": (1,), "terrain_shadow": (4,)},
}

_DTYPE = "uint16"
_DTYPE_ONE = np.uint16(1)


def _bit(name: str) -> int:
    if name not in FLAGS:
        raise ValueError(f"unknown flag {name!r}; choose from {sorted(FLAGS)}")
    return 1 << FLAGS[name]


def _as_2d(ds: xr.Dataset, name: str) -> np.ndarray | None:
    if name not in ds or ds[name].dims != ("y", "x"):
        return None
    return np.asarray(ds[name].values)


def _band_nearest(ds: xr.Dataset, var: str, wl: float, tol: float = 30.0):
    """The band nearest ``wl`` nm, or None when nothing is within ``tol``."""
    wls = np.asarray(ds[var]["wavelength"].values, dtype="float64")
    i = int(np.argmin(np.abs(wls - wl)))
    return None if abs(wls[i] - wl) > tol else ds[var].isel(wavelength=i)


def build(ds: xr.Dataset, *, var: str | None = None,
          derive: tuple[str, ...] = ("fill", "terrain_shadow"),
          negative_fraction: float = 0.1, slope_max: float = 45.0,
          zhai: bool = False, sources: bool = True, verbose: bool = False) -> xr.DataArray:
    """Fold every mask a dataset carries into one ``uint16`` flag layer.

    Args:
        ds: any hyperproc dataset. Whatever mask layers it has are used; what
            it lacks is simply absent from the result, never guessed.
        var: the cube to read for the derived flags; the main one by default.
        derive: flags to compute rather than read. ``"fill"`` marks pixels with
            no finite value in any usable band, ``"terrain_shadow"`` needs
            ``cos_i``, ``"steep_terrain"`` needs ``slope``,
            ``"negative_reflectance"`` reads the cube. The two defaults are the
            ones worth their cost on every sensor.
        negative_fraction: fraction of usable bands that must be below zero
            before ``negative_reflectance`` is set.
        slope_max: degrees above which ``steep_terrain`` is set.
        zhai: also run the Zhai cloud index from
            :mod:`hyperproc.correct.masks` where the bands it needs exist.
            Off by default: it is a decision, not a measurement, and providers
            that ship a cloud mask should be trusted over it.
        sources: read the provider's own layers. False derives only.
        verbose: print which layers were folded in.

    Returns:
        ``uint16`` ``(y, x)`` DataArray named ``quality``, with CF
        ``flag_masks`` and ``flag_meanings`` attributes so the bits travel with
        the data.

    Raises:
        ValueError: the dataset has no ``y``/``x`` dimensions.
    """
    from hyperproc.io import main_var
    if "y" not in ds.sizes or "x" not in ds.sizes:
        raise ValueError("quality.build needs a dataset with y and x dimensions")
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    q = np.zeros((ny, nx), dtype=_DTYPE)
    used: list[str] = []

    if sources:
        for name, (flag, when) in BOOLEAN_SOURCES.items():
            a = _as_2d(ds, name)
            if a is None:
                continue
            hit = (a.astype(bool) == bool(when))
            if not bool(when):                      # inverted layers say nothing where they are fill
                hit &= np.isfinite(a) if a.dtype.kind == "f" else True
            q[hit] |= _bit(flag)
            used.append(f"{name}->{flag}" + ("" if when else " (inverted)"))
        for name, table in CODED_SOURCES.items():
            a = _as_2d(ds, name)
            if a is None:
                continue
            for flag, codes in table.items():
                q[np.isin(a, list(codes))] |= _bit(flag)
            used.append(f"{name}->{'/'.join(table)}")

    derive = tuple(derive or ())
    cube = None
    if derive and ({"fill", "negative_reflectance"} & set(derive)):
        name = var or main_var(ds)
        if name in ds and "wavelength" in ds[name].dims:
            cube = ds[name]
            if "good_wavelength" in ds.coords:
                good = np.asarray(ds["good_wavelength"].values, dtype=bool)
                if good.any():
                    cube = cube.isel(wavelength=np.nonzero(good)[0])

    if "fill" in derive:
        if cube is None:
            warnings.warn("quality: cannot derive 'fill' without a wavelength cube", stacklevel=2)
        else:
            q[~np.asarray(np.isfinite(cube).any(dim="wavelength").values)] |= _bit("fill")
            used.append("fill<-cube")
    if "negative_reflectance" in derive:
        if cube is None:
            warnings.warn("quality: cannot derive 'negative_reflectance' without a cube", stacklevel=2)
        else:
            frac = np.asarray((cube < 0).sum(dim="wavelength").values) / max(1, cube.sizes["wavelength"])
            q[frac > negative_fraction] |= _bit("negative_reflectance")
            used.append(f"negative_reflectance<-cube (>{negative_fraction:.0%} of bands)")
    if "terrain_shadow" in derive:
        cos_i = _as_2d(ds, "cos_i")
        if cos_i is None:
            warnings.warn("quality: cannot derive 'terrain_shadow' without cos_i", stacklevel=2)
        else:
            q[np.isfinite(cos_i) & (cos_i <= 0)] |= _bit("terrain_shadow")
            used.append("terrain_shadow<-cos_i")
    if "steep_terrain" in derive:
        slope = _as_2d(ds, "slope")
        if slope is None:
            warnings.warn("quality: cannot derive 'steep_terrain' without slope", stacklevel=2)
        else:
            q[np.isfinite(slope) & (slope > slope_max)] |= _bit("steep_terrain")
            used.append(f"steep_terrain<-slope (>{slope_max:g} deg)")

    if zhai:
        from hyperproc.correct import masks
        name = var or main_var(ds)
        bands = {k: _band_nearest(ds, name, wl) for k, wl in
                 (("blue", 480), ("green", 560), ("red", 660), ("nir", 860),
                  ("swir1", 1600), ("swir2", 2200))}
        if any(bands[k] is None for k in ("blue", "green", "red", "nir")):
            warnings.warn("quality: the Zhai cloud index needs blue, green, red and NIR bands", stacklevel=2)
        else:
            arrays = {k: (None if v is None else np.asarray(v.values, dtype="float32"))
                      for k, v in bands.items()}
            valid = ~decode(xr.DataArray(q, dims=("y", "x")), "fill").values
            cloud = masks.zhai_cloud(arrays["blue"], arrays["green"], arrays["red"], arrays["nir"],
                                     arrays["swir1"], arrays["swir2"], valid=valid)
            q[np.asarray(cloud, dtype=bool)] |= _bit("cloud")
            used.append("cloud<-zhai index")

    # Nothing was observed at a fill pixel, so no other condition can be asserted
    # there. Without this, an inverted or absent provider layer reads as a positive
    # detection over the whole off-swath region.
    fill_set = (q & _bit("fill")) > 0
    if fill_set.any():
        q[fill_set] = _DTYPE_ONE * _bit("fill")

    if verbose:
        print(f"quality: {len(used)} source(s) folded in")
        for u in used:
            print(f"    {u}")

    out = xr.DataArray(q, dims=("y", "x"),
                       coords={c: ds[c] for c in ("y", "x") if c in ds.coords}, name="quality")
    out.attrs.update(
        long_name="per-pixel quality flags",
        standard_name="quality_flag",
        flag_masks=" ".join(str(1 << b) for b in FLAGS.values()),
        flag_meanings=" ".join(FLAGS),
        flag_bits=" ".join(f"{n}:{b}" for n, b in FLAGS.items()),
        sources=", ".join(used) or "none",
        note="bit set = condition present; 0 = nothing flagged",
    )
    return out


def decode(quality, *names: str) -> xr.DataArray | np.ndarray:
    """True where any of the named flags is set.

    With no names, true where **any** flag is set.
    """
    wanted = list(names) or list(FLAGS)
    mask = 0
    for n in wanted:
        mask |= _bit(n)
    if isinstance(quality, xr.DataArray):
        out = (quality & mask) > 0
        out.attrs.update(long_name="quality mask: " + " or ".join(wanted))
        return out
    return (np.asarray(quality) & mask) > 0


def set_flag(quality: xr.DataArray, name: str, mask) -> xr.DataArray:
    """Return a copy of ``quality`` with ``name`` set wherever ``mask`` is true."""
    out = quality.copy()
    m = np.asarray(mask if not isinstance(mask, xr.DataArray) else mask.values, dtype=bool)
    values = np.asarray(out.values).copy()
    values[m] |= _bit(name)
    out.values = values
    prev = out.attrs.get("sources", "")
    out.attrs["sources"] = f"{prev}, {name}<-set_flag" if prev and prev != "none" else f"{name}<-set_flag"
    return out


def summary(quality) -> dict:
    """Fraction of pixels carrying each flag, plus ``clear`` for none of them."""
    q = np.asarray(quality.values if isinstance(quality, xr.DataArray) else quality)
    n = q.size or 1
    out = {name: float(((q & (1 << bit)) > 0).sum()) / n for name, bit in FLAGS.items()}
    out["clear"] = float((q == 0).sum()) / n
    return out


def apply(ds: xr.Dataset, quality: xr.DataArray | None = None,
          drop: tuple[str, ...] = DEFAULT_DROP, var: str | None = None,
          keep: bool = True, derive: tuple[str, ...] = ("fill",)) -> xr.Dataset:
    """Set the cube to NaN wherever a dropped flag is set.

    Args:
        ds: the dataset to mask.
        quality: a layer from :func:`build`; built here when omitted.
        drop: the flags to mask on. The default is the set almost no analysis
            wants: fill, cloud, cloud shadow and cirrus.
        var: the cube to mask; the main one by default.
        keep: attach the quality layer to the result as ``quality``.
        derive: passed to :func:`build` when ``quality`` is not given. The
            default derives only ``fill``, the one flag in ``DEFAULT_DROP``
            that no provider layer supplies directly.

    Returns:
        A copy of ``ds``, lazy where ``ds`` was lazy.
    """
    from hyperproc.io import main_var
    q = build(ds, var=var, derive=derive) if quality is None else quality
    name = var or main_var(ds)
    bad = decode(q, *drop)
    out = ds.copy()
    out[name] = ds[name].where(~bad)
    out[name].attrs.update(ds[name].attrs)
    out[name].attrs["quality_masked"] = ", ".join(drop)
    if keep:
        out["quality"] = q
    out.attrs["quality_masked"] = ", ".join(drop)
    return out


def describe(quality=None) -> str:
    """The bit table, with the share of pixels per flag when a layer is given."""
    stats = summary(quality) if quality is not None else None
    lines = ["bit  flag                  " + ("share    " if stats else "") + "meaning",
             "---  --------------------  " + ("-------  " if stats else "") + "-" * 46]
    for name, bit in FLAGS.items():
        share = f"{stats[name] * 100:6.2f} %  " if stats else ""
        lines.append(f"{bit:3d}  {name:20s}  {share}{FLAG_DESCRIPTIONS[name]}")
    if stats:
        lines.append(f"     {'clear (no flag)':20s}  {stats['clear'] * 100:6.2f} %")
    return "\n".join(lines)
