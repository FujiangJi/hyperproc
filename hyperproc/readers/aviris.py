"""AVIRIS reader - Classic, NG, 3 and 5, radiance and reflectance.

Four instruments in one JPL family, spanning thirty years and two file formats.
All four ship **orthorectified** cubes, so unlike EMIT or PACE there is no GLT
to apply to the image itself - the reader hands back a map-projected grid.

================  ==========================  =====  ===========================
instrument        granule id                  bands  cube
================  ==========================  =====  ===========================
AVIRIS-Classic    ``f201013t01p00r10``          224  ``*_sc01_ort_img``,
                                                     ``*_corr_*_img``  (ENVI)
AVIRIS-NG         ``ang20220224t210144``        425  ``*_rdn_*_img``,
                                                     ``*_rfl_*_img``   (ENVI)
AVIRIS-3          ``AV320231005t181518``        284  ``*_RDN_ORT``,
                                                     ``*_RFL_ORT``     (ENVI)
AVIRIS-5          ``AV520250508t173511_000``    424  ``*_RDN.nc``,
                                                     ``*_RFL_ORT.nc`` (NetCDF-4)
================  ==========================  =====  ===========================

Six things to know:

1. **The grids are flight-aligned, not north-up.** Every ENVI variant carries a
   ``rotation`` in its ``map info`` - -13 deg for the AVIRIS-3 line here, -50
   for the NG one, +29 for Classic - so the affine has non-zero shear terms and
   the 1-D ``x``/``y`` coordinates cannot describe it on their own.
   ``attrs["transform"]`` (GDAL order) is the authoritative georeferencing;
   pass ``map_coords=True`` for exact 2-D ``easting``/``northing``. AVIRIS-5 is
   the exception - it ships a north-up NetCDF grid.

2. **Classic radiance is scaled integers.** The cube is big-endian ``int16``
   and must be divided by the per-band factors in the ``.gain`` sidecar (300,
   600 or 1200 here) to reach uW nm-1 cm-2 sr-1. NG and AVIRIS-3 store float
   radiance in those units already. Reflectance is unitless 0-1 everywhere.

3. **Geometry lives in a separate file, often a separate directory.** The OBS
   cube carries path length, view and solar angles, slope, aspect and
   ``cos_i`` - everything topographic and BRDF correction needs. For NG and
   Classic the reflectance and radiance ship as two sibling folders and only
   the radiance one holds the OBS, so the reader searches sibling directories
   for the same granule id.

4. **AVIRIS-5's two levels are not on the same grid.** Its L2A reflectance is
   orthorectified, but its OBS *and* its L1B radiance are raw ``(line,
   sample)`` and ship their own lookup table, so the reader applies that GLT to
   bring them onto the reflectance grid. The other three deliver ``*_obs_ort``
   and ortho cubes throughout. Note the radiance is a separate ORNL DAAC
   collection (``AV5_L1B_RDN``) from the L2A bundle, so a folder holding only
   L2A products genuinely has no radiance in it.

5. **AVIRIS-3's slope and cos_i are wrong as delivered.** Slope is stored from
   *vertical*, and ``cos_i`` is computed from that, which leaves both unusable
   for topographic correction. This is not assumed per instrument: every
   variant ships a DEM, so :func:`check_geometry` differentiates it and decides
   from the correlation, and :func:`fix_slope_convention` rebuilds the pair
   when the verdict says so. ``fix_geometry=False`` returns the file untouched.

6. **No-data is not -9999 everywhere.** Classic radiance declares none in its
   header and fills off-swath cells with -50, which survives the gain division
   as -0.167 and drags a scene median negative if it is not masked.

Cubes here run 10-30 GB, so they are opened lazily through dask; nothing is
read until you slice or compute. ``wl_range`` subsets bands before any read.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

import warnings

from hyperproc.readers._common import crs_text, datetime_from_id, finish_bands, normalise_angles

import numpy as np
import xarray as xr

from hyperproc.geometry import check_geometry, fix_slope_convention  # noqa: F401  re-exported

FILL = -9999.0

#: AVIRIS-Classic orthorectified *radiance* carries no ``data ignore value`` in
#: its header and does not use -9999: off-swath cells hold -50 in DN space,
#: uniformly (both corners of the line here are 100% that single value). Left
#: unmasked it survives the gain division as -0.1667 and drags the scene median
#: negative. The reflectance product is float and already uses NaN.
CLASSIC_RDN_FILL = -50.0

#: Water-vapour windows to blank when a product ships no ``bbl``. Taken from
#: the AVIRIS-3 bad-band list, which flags 1350.8-1432.7 and 1804.7-1968.1 nm.
WATER_BANDS = ((1340.0, 1440.0), (1800.0, 1975.0))

#: OBS band name fragment -> our name. The band order is identical across
#: Classic (10 bands), NG and AVIRIS-3 (11, adding earth-sun distance), but the
#: spelling is not - "Cosine(i)" vs "cosine i", "Solar phase" vs "phase".
OBS_BANDS = (
    ("path length", "path_length"),
    ("to-sensor azimuth", "vaa"),
    ("to-sensor zenith", "vza"),
    ("to-sun azimuth", "saa"),
    ("to-sun zenith", "sza"),
    ("phase", "phase"),
    ("slope", "slope"),
    ("aspect", "aspect"),
    ("cosine", "cos_i"),
    ("utc time", "utc_time"),
    ("earth-sun distance", "earth_sun_distance"),
)

OBS_UNITS = {
    "path_length": ("m", "sensor-to-ground path length"),
    "vaa": ("degrees", "to-sensor azimuth, cw from north"),
    "vza": ("degrees", "to-sensor zenith"),
    "saa": ("degrees", "to-sun azimuth, cw from north"),
    "sza": ("degrees", "to-sun zenith"),
    "phase": ("degrees", "solar phase angle"),
    "slope": ("degrees", "terrain slope"),
    "aspect": ("degrees", "terrain aspect, cw from north"),
    "cos_i": ("1", "cosine of the solar incidence angle on the slope"),
    "utc_time": ("hours", "UTC time of acquisition"),
    "earth_sun_distance": ("AU", "earth-sun distance"),
}

#: AVIRIS-5 stores the same fields under spelled-out NetCDF names.
AV5_OBS = {
    "path_length": "path_length", "to_sensor_azimuth": "vaa",
    "to_sensor_zenith": "vza", "to_sun_azimuth": "saa",
    "to_sun_zenith": "sza", "solar_phase": "phase", "slope": "slope",
    "aspect": "aspect", "cosine_i": "cos_i", "utc_time": "utc_time",
    "earth_sun_distance": "earth_sun_distance",
}


#: Where each variant keeps a DEM, as (globs, 1-based band, GLT globs).
#: Only AVIRIS-3 delivers elevation already gridded; the others hand over the
#: raw sensor grid plus a lookup table. AVIRIS-5 carries ``elev`` in its OBS
#: file and is handled with the rest of its geometry.
ELEVATION = {
    "AVIRIS-3": (("*_LOC_ORT",), 3, ()),
    "AVIRIS-NG": (("*_loc", "*_igm"), 3, ("*_glt",)),
    "AVIRIS-Classic": (("*_ort_igm",), 3, ("*_ort_glt",)),
}

#: Layers a topographic or BRDF correction consumes, in a sensible plot order.
TOPO_LAYERS = ("slope", "aspect", "cos_i", "sza", "saa", "vza", "vaa", "raa",
               "elev", "path_length")


@dataclass(frozen=True)
class _Variant:
    """How one instrument names its files."""

    name: str
    granule: re.Pattern
    rdn: tuple[str, ...]
    rfl: tuple[str, ...]
    obs: tuple[str, ...]
    unc: tuple[str, ...] = ()
    atm: tuple[str, ...] = ()


VARIANTS = (
    _Variant(
        "AVIRIS-3", re.compile(r"(AV3\d{8}t\d{6})"),
        rdn=("*_RDN_ORT",), rfl=("*_RFL_ORT",), obs=("*_OBS_ORT",),
        unc=("*_UNC_ORT",), atm=("*_ATM_ORT",),
    ),
    _Variant(
        "AVIRIS-5", re.compile(r"(AV5\d{8}t\d{6}_\d{3})"),
        rdn=("*_L1B_RDN_*_RDN.nc",), rfl=("*_RFL_ORT.nc",),
        obs=("*_L1B_ORT_*_OBS.nc",), unc=("*_UNC_ORT.nc",),
    ),
    _Variant(
        "AVIRIS-NG", re.compile(r"(ang\d{8}t\d{6})"),
        rdn=("*_rdn_*_img",), rfl=("*_rfl_*_img",), obs=("*_obs_ort",),
    ),
    _Variant(
        "AVIRIS-Classic", re.compile(r"(f\d{6}t\d{2}p\d{2}r\d{2})"),
        rdn=("*_sc01_ort_img", "*rdn*_ort_img"),
        rfl=("*_corr_*_img", "*_refl_*_img"),
        obs=("*_obs_ort",), atm=("*_h2o_*_img",),
    ),
)


def open_aviris(
    path: str | Path,
    product: str | None = None,
    wl_range: tuple[float, float] | None = None,
    good_bands_only: bool = False,
    geometry: bool = True,
    extras: bool = True,
    uncertainty: bool = False,
    fix_geometry: bool | str = "auto",
    sort_bands: bool = True,
    ortho: bool = True,
    fill: float | None = None,
    map_coords: bool = False,
    chunks: str | int | dict | None = "auto",
) -> xr.Dataset:
    """Open an AVIRIS-Classic, -NG, -3 or -5 flightline.

    Args:
        path: the cube, its ``.hdr``, or the directory holding it. A directory
            is searched for a radiance or reflectance cube; if it holds both,
            pass ``product=`` to choose.
        product: ``"reflectance"`` or ``"radiance"``. Inferred from the
            filename when you point at a cube, required only to break a tie.
        wl_range: ``(min_nm, max_nm)``, applied before any data is read.
        good_bands_only: NaN out the water-vapour bands, keeping the band count
            so indices stay aligned with the instrument's own grid. Uses the
            product's ``bbl`` when it ships one (AVIRIS-3 flags 35 of 284
            bands) and :data:`WATER_BANDS` otherwise.
        geometry: attach the OBS layers - ``sza``, ``saa``, ``vza``, ``vaa``,
            ``slope``, ``aspect``, ``cos_i``, ``path_length`` - plus a derived
            ``raa``. Searches sibling directories for the granule's OBS file.
        extras: attach the atmospheric state - ``aot``/``wv`` for AVIRIS-3 and
            -5, the three-phase water retrieval for Classic.
        uncertainty: attach the per-band posterior uncertainty cube where one
            ships (AVIRIS-3, -5). Doubles the data volume.
        fix_geometry: ``"auto"`` (default) runs :func:`check_geometry`, which
            differentiates the granule's own DEM and corrects ``slope`` and
            ``cos_i`` only if the product actually stores slope from vertical -
            AVIRIS-3 does, the other three do not, and the verdict lands in
            ``attrs["geometry_check"]``. ``True`` forces the correction,
            ``False`` returns every layer exactly as the file has it.
        ortho: AVIRIS-5 only, and only for L1B. Its radiance ships on the raw
            2000 x 1239 sensor grid with a lookup table, unlike its already
            gridded L2A reflectance, so this applies that GLT to put the two
            levels on the same map grid. ``False`` returns the sensor grid,
            which then carries no CRS or transform. The ENVI instruments
            deliver orthorectified cubes and ignore this.
        sort_bands: put the bands in ascending wavelength order. AVIRIS-Classic
            reads out four spectrometers whose ranges overlap at the joins, so
            its wavelengths step *backwards* three times - 667.5 -> 655.5 nm at
            band 31, and again at 95 and 159. That leaves the coordinate
            non-monotonic, and ``sel(wavelength=..., method="nearest")`` raises
            rather than returning a band. Sorting is a permutation, so nothing
            is lost, and ``band_index`` keeps each band's original position in
            the file. A no-op for NG, AVIRIS-3 and -5, which are already sorted.
        fill: override the no-data value. Otherwise taken from the ENVI
            header's ``data ignore value``, falling back to -50 for Classic
            radiance, which declares none (see :data:`CLASSIC_RDN_FILL`), and
            to -9999 for AVIRIS-5.
        map_coords: add exact 2-D ``easting``/``northing``. The flight-aligned
            grids are rotated, so the 1-D ``x``/``y`` follow the top row and
            left column only; this computes the full affine per pixel at the
            cost of two float64 arrays the size of the image.
        chunks: dask chunking for the cube. ``"auto"`` keeps a 10-30 GB
            flightline lazy and chunks along ``y`` only, matching the
            line-major layout on disk so a spatial subset is one sequential
            read; ``None`` reads the cube into memory eagerly.

    Returns:
        ``xarray.Dataset`` with ``reflectance`` or ``radiance`` on
        ``(y, x, wavelength)``, ``wavelength``/``fwhm`` coordinates in nm, and
        ``attrs["transform"]`` in GDAL order carrying the grid rotation.

    Raises:
        FileNotFoundError: no cube matched, or a directory held none.
        ValueError: the filename is not a recognised AVIRIS granule, or a
            directory holds both products and ``product=`` was not given.
    """
    path = Path(path)
    variant, granule = _identify(path)
    cube, product = _find_cube(path, variant, granule, product)

    if variant.name == "AVIRIS-5":
        ds = _open_av5(cube, granule, wl_range, uncertainty, chunks, fill, ortho)
    else:
        ds = _open_envi(cube, variant, granule, product, wl_range, chunks,
                        fill, sort_bands)

    if good_bands_only:
        _blank_water_bands(ds)
    if map_coords:
        _add_map_coords(ds)
    if geometry:
        _add_geometry(ds, cube, variant, granule, chunks)
        _add_elevation(ds, cube, variant, granule)
        if fix_geometry:
            report = (check_geometry(ds) if fix_geometry == "auto"
                      else {"needs_fix": True, "evidence": "fix_geometry=True",
                            "convention": "vertical"})
            ds.attrs["geometry_check"] = report.get("evidence", "")
            ds.attrs["slope_convention"] = report.get("convention", "unknown")
            if report["needs_fix"]:
                fix_slope_convention(ds)
    if extras:
        _add_extras(ds, cube, variant, granule, chunks)
    if uncertainty and variant.name != "AVIRIS-5":
        _add_uncertainty(ds, cube, variant, granule, chunks)
    return ds


# --- identification ------------------------------------------------------


def _identify(path: Path) -> tuple[_Variant, str]:
    """Work out the instrument and granule id from a path.

    Checks the path's own name first, then walks up - a bare directory such as
    ``ang20220224t210144_rfl_v2aa1/`` names the granule even though the files
    inside repeat it.
    """
    for part in (path.name, *(p.name for p in path.parents)):
        for variant in VARIANTS:
            m = variant.granule.search(part)
            if m:
                return variant, m.group(1)
    raise ValueError(
        f"{path.name!r} is not a recognised AVIRIS granule. Expected an id like "
        f"f201013t01p00r10 (Classic), ang20220224t210144 (NG), "
        f"AV320231005t181518 (AVIRIS-3) or AV520250508t173511_000 (AVIRIS-5)."
    )


def _find_cube(path: Path, variant: _Variant, granule: str,
               product: str | None) -> tuple[Path, str]:
    """Resolve a cube path, accepting the binary, its .hdr, or a directory."""
    if path.is_file():
        cube = path.with_suffix("") if path.suffix == ".hdr" else path
        return cube, product or _guess_product(cube, variant)

    if not path.is_dir():
        raise FileNotFoundError(path)

    found = {}
    for kind, globs in (("radiance", variant.rdn), ("reflectance", variant.rfl)):
        hit = _search(path, granule, globs, roots=[path])
        if hit:
            found[kind] = hit
    if product:
        if product not in found:
            raise FileNotFoundError(
                f"no {product} cube for {granule} in {path}. Found: "
                f"{sorted(found) or 'nothing'}"
            )
        return found[product], product
    if len(found) > 1:
        raise ValueError(
            f"{path} holds both a radiance and a reflectance cube for {granule}. "
            f"Pass product='reflectance' or product='radiance'."
        )
    if not found:
        raise FileNotFoundError(f"no AVIRIS cube for {granule} in {path}")
    kind, cube = next(iter(found.items()))
    return cube, kind


def _guess_product(cube: Path, variant: _Variant) -> str:
    for kind, globs in (("radiance", variant.rdn), ("reflectance", variant.rfl)):
        for g in globs:
            if cube.match(g):
                return kind
    raise ValueError(
        f"cannot tell whether {cube.name!r} is radiance or reflectance. "
        f"Pass product='reflectance' or product='radiance'."
    )


def _search(start: Path, granule: str, globs: tuple[str, ...],
            roots: list[Path] | None = None) -> Path | None:
    """Find a granule's sibling file, looking in nearby directories.

    NG and Classic split a flightline into ``*_rdn_*`` and ``*_rfl_*`` folders
    and put the OBS in the radiance one, so opening reflectance means looking
    one level up and back down.
    """
    if roots is None:
        roots = [start]
        parent = start.parent
        if parent.is_dir():
            roots += [d for d in sorted(parent.iterdir())
                      if d.is_dir() and granule in d.name and d != start]
    for root in roots:
        for g in globs:
            hits = sorted(p for p in root.glob(g)
                          if granule in p.name and p.suffix != ".hdr")
            if len(hits) > 1:
                warnings.warn(f"{granule}: {len(hits)} files match {g} in {root} "
                              f"({', '.join(h.name for h in hits[:4])}); using {hits[0].name}")
            if hits:
                return hits[0]
    return None


def _sibling(cube: Path, granule: str, globs: tuple[str, ...]) -> Path | None:
    return _search(cube.parent, granule, globs) if globs else None


# --- ENVI ----------------------------------------------------------------


def read_hdr(path: str | Path) -> dict[str, str]:
    """Parse an ENVI ``.hdr`` into a dict of raw strings.

    Handles the quirks in the AVIRIS family: brace-delimited values spanning
    many lines, leading whitespace on keys (Classic indents ``wavelength`` and
    ``fwhm``), and ``map info ={`` with no space before the brace.
    """
    text = Path(path).read_text(errors="replace")
    out = {}
    for m in re.finditer(r"^[ \t]*([\w ]+?)[ \t]*=[ \t]*(\{.*?\}|.*?)[ \t]*$",
                         text, re.M | re.S):
        key, val = m.group(1).strip().lower(), m.group(2).strip()
        if val.startswith("{"):
            val = val[1:-1] if val.endswith("}") else val[1:]
        out[key] = " ".join(val.split())
    return out


def _good_bands(wl: np.ndarray, bbl: np.ndarray | None) -> tuple[np.ndarray, str]:
    """The usable-band flag, and where it came from.

    AVIRIS-3 is the only variant that ships a ``bbl``. For the other three the
    flag is derived from :data:`WATER_BANDS` so the coordinate - and the band
    CSV written from it - is populated for every instrument rather than blank
    on three of four. ``good_bands_source`` in the attrs records which it is,
    because the provider's judgement and ours are not the same thing.
    """
    if bbl is not None:
        return bbl > 0, "provider bbl"
    bad = np.zeros(wl.shape, bool)
    for lo, hi in WATER_BANDS:
        bad |= (wl >= lo) & (wl <= hi)
    return ~bad, "water-vapour windows"


def _fill_value(hdr: dict, variant: _Variant, product: str) -> float:
    """What counts as no-data, preferring what the header actually says."""
    raw = hdr.get("data ignore value", "")
    try:
        return float(raw)
    except (TypeError, ValueError):
        pass
    if variant.name == "AVIRIS-Classic" and product == "radiance":
        return CLASSIC_RDN_FILL
    return FILL


def _hdr_array(hdr: dict, key: str) -> np.ndarray | None:
    if key not in hdr:
        return None
    try:
        return np.array([float(v) for v in hdr[key].split(",") if v.strip()])
    except ValueError:
        return None


def _chunks_for(cube: Path, spec, nx: int | None = None, nbands: int | None = None):
    """Turn ``chunks="auto"`` into a spec that matches how ENVI stores the cube.

    Both interleaves AVIRIS uses are line-major - BIL keeps a whole line of
    every band together, BIP a whole line of every sample - so GDAL's block is
    one image line. Dask's own "auto" chunks per band instead, which makes a
    small spatial subset pull every band in full: slicing 200x200 pixels out of
    a 11 GB flightline reads all 11 GB. Chunking along ``y`` only, keeping all
    bands and samples together, turns that into one sequential read.
    """
    if spec != "auto":
        return spec
    if nx is None or nbands is None:
        return True
    row_bytes = max(1, nx * nbands * 4)
    rows = int(np.clip(64 * 1024 * 1024 // row_bytes, 1, 2048))
    return {"band": -1, "y": rows, "x": -1}


def _open_envi(cube: Path, variant: _Variant, granule: str, product: str,
               wl_range, chunks, fill, sort_bands=True) -> xr.Dataset:
    """Open one of the three ENVI variants."""
    import rioxarray

    hdr_path = _hdr_for(cube)
    hdr = read_hdr(hdr_path)
    wl = _hdr_array(hdr, "wavelength")
    fwhm = _hdr_array(hdr, "fwhm")
    if wl is None:
        wl, fwhm = _read_spc(cube, granule)
    if wl is None:
        raise ValueError(
            f"{hdr_path.name} lists no wavelengths and no .spc sidecar was found "
            f"beside {cube.name}. Without band centres the cube cannot be read "
            f"as a spectral dataset."
        )
    if wl.max() < 100:  # a few headers give micrometres
        wl, fwhm = wl * 1000.0, (fwhm * 1000.0 if fwhm is not None else None)

    nb = int(hdr.get("bands", 0) or 0) or (len(wl) if wl is not None else 0)
    nx = int(hdr.get("samples", 0) or 0)
    da = rioxarray.open_rasterio(cube, chunks=_chunks_for(cube, chunks, nx, nb),
                                 masked=False)
    keep = _band_subset(wl, wl_range)
    if keep is not None:
        da = da.isel(band=keep)

    bbl = _hdr_array(hdr, "bbl")
    if bbl is not None and bbl.size != nb:
        bbl = None
    scale = _gain(cube, granule) if product == "radiance" else None
    index = np.arange(nb)
    if keep is not None:
        wl, index = wl[keep], index[keep]
        fwhm = fwhm[keep] if fwhm is not None else None
        bbl = bbl[keep] if bbl is not None else None
        scale = scale[keep] if scale is not None else None

    # Classic's four spectrometers overlap, so its wavelengths step backwards
    # three times and xarray cannot index the coordinate. Sorting is a
    # permutation; band_index remembers where each band came from.
    reordered = False
    if sort_bands and wl.size > 1 and np.any(np.diff(wl) <= 0):
        order = np.argsort(wl, kind="stable")
        da = da.isel(band=order)
        wl, index = wl[order], index[order]
        fwhm = fwhm[order] if fwhm is not None else None
        bbl = bbl[order] if bbl is not None else None
        scale = scale[order] if scale is not None else None
        reordered = True

    var = "reflectance" if product == "reflectance" else "radiance"
    nodata = _fill_value(hdr, variant, product) if fill is None else fill
    arr = da.astype("float32").where(da != nodata)
    if scale is not None:
        arr = arr / xr.DataArray(scale.astype("float32"), dims="band")

    ds = xr.Dataset(
        {var: (("wavelength", "y", "x"), arr.data)},
        coords={"wavelength": ("wavelength", wl.astype("float64"))},
    ).transpose("y", "x", "wavelength")
    if fwhm is not None:
        ds.coords["fwhm"] = ("wavelength", fwhm.astype("float64"))

    good, good_src = _good_bands(wl, bbl)
    ds.coords["good_wavelength"] = ("wavelength", good)
    ds["good_wavelength"].attrs["long_name"] = f"usable band ({good_src})"
    ds.coords["band_index"] = ("wavelength", index)
    ds["band_index"].attrs["long_name"] = "0-based band position in the source file"

    units = ("1" if product == "reflectance"
             else "uW nm-1 cm-2 sr-1")
    ds.attrs.update(
        sensor=variant.name, level="L2A" if product == "reflectance" else "L1B",
        granule=granule, product=product, units=units, orthorectified=1,
        crs=crs_text(da.rio.crs), transform=tuple(da.rio.transform().to_gdal()),
        rotation_deg=_rotation(hdr), description=hdr.get("description", ""),
        source=cube.name, fill_value=nodata,
        bands_reordered=int(reordered), good_bands_source=good_src,
        # AVIRIS ids name the flight line, not the product - see default_name.
        stem=f"{granule}_{'L2A' if product == 'reflectance' else 'L1B'}",
    )
    if ds.attrs["crs"] is None:
        # No map info in the ENVI header: the cube sits on the sensor grid, so
        # neither a CRS nor a (identity) transform may be advertised.
        for k in ("crs", "transform"):
            ds.attrs.pop(k, None)
        ds.attrs.update(grid="sensor", orthorectified=0)
        warnings.warn(f"{cube.name}: no map info in the ENVI header - the cube is not "
                      "georeferenced (attrs['grid'] = 'sensor'); to_geotiff will refuse it")
    _finish(ds, var, units, product)
    finish_bands(ds, datetime=datetime_from_id(granule))
    normalise_angles(ds)
    return ds


def _hdr_for(cube: Path) -> Path:
    """ENVI headers are either ``cube.hdr`` or ``cube.<ext>.hdr``."""
    for cand in (cube.with_suffix(cube.suffix + ".hdr"), cube.with_suffix(".hdr")):
        if cand.is_file():
            return cand
    raise FileNotFoundError(f"no ENVI header beside {cube}")


def _rotation(hdr: dict) -> float:
    m = re.search(r"rotation\s*=\s*(-?[\d.]+)", hdr.get("map info", ""))
    return float(m.group(1)) if m else 0.0


def _read_spc(cube: Path, granule: str) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Classic keeps band centres and widths in a two-column ``.spc``."""
    spc = _search(cube.parent, granule, ("*.spc",))
    if spc is None:
        return None, None
    vals = np.loadtxt(spc, usecols=(0, 1))
    return vals[:, 0], vals[:, 1]


def _gain(cube: Path, granule: str) -> np.ndarray | None:
    """Classic radiance is ``DN / gain``; the sidecar holds one factor per band.

    NG and AVIRIS-3 ship float radiance already in uW nm-1 cm-2 sr-1 and have
    no gain file, so this returns None for them.
    """
    gain = _search(cube.parent, granule, ("*.gain",))
    if gain is None:
        return None
    return np.loadtxt(gain, usecols=(0,))


def _band_subset(wl: np.ndarray | None, wl_range) -> np.ndarray | None:
    if wl_range is None or wl is None:
        return None
    lo, hi = wl_range
    keep = np.where((wl >= lo) & (wl <= hi))[0]
    if keep.size == 0:
        raise ValueError(f"no bands in {wl_range} nm; "
                         f"this granule covers {wl.min():.1f}-{wl.max():.1f} nm")
    return keep


# --- AVIRIS-5 ------------------------------------------------------------


def _open_av5(cube: Path, granule: str, wl_range, uncertainty, chunks,
              fill=None, ortho=True) -> xr.Dataset:
    """AVIRIS-5 ships CF-1.6 NetCDF, but its two levels are not on the same grid.

    L2A reflectance (``*_RFL_ORT.nc``) is already orthorectified - 2009 x 3605
    here, with ``easting``/``northing`` at the file root. L1B radiance
    (``*_L1B_RDN_*_RDN.nc``) is **not**: it is the raw 2000 x 1239 sensor grid
    with a lookup table alongside it, exactly like the OBS file. So the reader
    applies that GLT to put radiance on the same map grid as reflectance, which
    is what makes the two levels comparable pixel for pixel.
    """
    import h5py

    group = _av5_cube_group(cube)
    crs, transform = _av5_grid(cube)
    with h5py.File(cube, "r") as h:
        glt = h.get("geolocation_lookup_table")
        sample = glt["sample"][:] if glt is not None else None
        line = glt["line"][:] if glt is not None else None

    ds = xr.open_dataset(cube, group=group,
                         chunks=chunks if chunks != "auto" else {})
    cube_var = next(k for k, v in ds.data_vars.items() if v.ndim == 3)
    product = "radiance" if "radiance" in cube_var else "reflectance"
    var = product
    if cube_var != var:
        ds = ds.rename({cube_var: var})
    dims = ds[var].dims
    ds = ds.rename({dims[0]: "wavelength", dims[1]: "y", dims[2]: "x"})
    ds = ds.set_coords([c for c in ("wavelength", "fwhm") if c in ds])

    keep = _band_subset(ds["wavelength"].values, wl_range)
    if keep is not None:
        ds = ds.isel(wavelength=keep)

    nodata = FILL if fill is None else fill
    ds[var] = ds[var].where(ds[var] != nodata)

    # A GLT that is larger than the cube means the cube is on the sensor grid.
    raw = sample is not None and sample.shape != (ds.sizes["y"], ds.sizes["x"])
    gridded = not raw or ortho
    if raw and ortho:
        # Rebuilt rather than assigned into: the gridded cube is 2009 x 3605
        # against the sensor grid's 2000 x 1239, so writing it back into the
        # open dataset just raises on the dimension clash.
        mapped = _glt_cube(ds[var], sample, line)
        ds = xr.Dataset({var: mapped}, coords={
            k: v for k, v in ds.coords.items() if k in ("wavelength", "fwhm")})

    ds = ds.transpose("y", "x", "wavelength")

    unc_name = "none"
    if uncertainty and product != "reflectance":
        warnings.warn(f"{granule}: AVIRIS-5 ships uncertainty for L2A reflectance only; "
                      "none attached to the radiance cube")
    elif uncertainty:
        unc = _sibling(cube, granule, ("*_UNC_ORT.nc",))
        if unc is not None:
            unc_name = unc.name
            u = xr.open_dataset(unc, group=_av5_cube_group(unc),
                                chunks=chunks if chunks != "auto" else {})
            name = next(k for k, v in u.data_vars.items() if v.ndim == 3)
            arr = u[name]
            arr = arr.rename(dict(zip(arr.dims, ("wavelength", "y", "x"))))
            if keep is not None:
                arr = arr.isel(wavelength=keep)
            ds[f"{var}_uncertainty"] = (
                ("y", "x", "wavelength"),
                arr.where(arr != FILL).transpose("y", "x", "wavelength").data)
            ds[f"{var}_uncertainty"].attrs.update(
                units="1", long_name="posterior reflectance uncertainty")

    good, good_src = _good_bands(ds["wavelength"].values, None)
    ds.coords["good_wavelength"] = ("wavelength", good)
    ds["good_wavelength"].attrs["long_name"] = f"usable band ({good_src})"

    grid = xr.open_dataset(cube)
    units = "uW nm-1 cm-2 sr-1" if product == "radiance" else "1"
    ds.attrs = {}
    ds.attrs.update(
        sensor="AVIRIS-5", level="L1B" if product == "radiance" else "L2A",
        granule=granule, product=product, units=units,
        orthorectified=int(gridded), crs=crs_text(crs), transform=transform,
        rotation_deg=0.0, source=cube.name, fill_value=nodata, bands_reordered=0,
        good_bands_source=good_src,
        stem=f"{granule}_{'L1B' if product == 'radiance' else 'L2A'}",
        description=str(grid.attrs.get("title", "")),
        datetime=str(grid.attrs.get("time_coverage_start", "")),
        uncertainty_source=unc_name,
    )
    if raw and not ortho:
        # A sensor-grid cube has no map transform; saying otherwise would let
        # to_geotiff write a georeferenced file that is quietly wrong.
        for k in ("crs", "transform"):
            ds.attrs.pop(k, None)
        ds.attrs["grid"] = "sensor"
    _finish(ds, var, units, product)
    finish_bands(ds, index=keep if keep is not None else None)
    normalise_angles(ds)
    grid.close()
    return ds


def _gather(block, li, si, void):
    """Pull one band-chunk of a bounded source window onto an output tile."""
    out = block[:, li, si]
    out[:, void] = np.nan
    return out


def _glt_cube(cube: xr.DataArray, sample: np.ndarray, line: np.ndarray,
              tile: int = 512) -> xr.DataArray:
    """Orthorectify a ``(wavelength, y, x)`` cube through a JPL lookup table.

    Done lazily and in tiles. The lazy part matters because the output here is
    424 x 2009 x 3605 floats - 12 GB against the sensor grid's 4 GB, most of it
    the void around a rotated flight strip - so materialising it to hand back a
    dataset would defeat opening the cube lazily at all.

    The tiling matters just as much. Gathering into chunks that span the whole
    grid means any spatial subset, however small, computes every pixel of every
    band in the chunk: a 100 x 100 window took minutes. Because the lookup
    table is spatially coherent, each output tile only ever reads a bounded
    window of the sensor grid, which is computed here at graph-build time.

    Indices are 1-based with 0 for "no data"; a negative index marks a cell
    filled from a neighbour rather than sampled directly, so both signs point at
    a real pixel and only the zeros are dropped.
    """
    import dask.array as dsk

    ny, nx = sample.shape
    nb = cube.sizes["wavelength"]
    ry, rx = cube.sizes["y"], cube.sizes["x"]
    s_all = np.clip(np.abs(sample).astype(np.int64) - 1, 0, rx - 1)
    l_all = np.clip(np.abs(line).astype(np.int64) - 1, 0, ry - 1)
    void_all = (sample == 0) | (line == 0)

    # Chunk the source spatially as well as by band, matching the file's own
    # HDF5 chunking. With whole-slab chunks a single output tile pulls all 4 GB
    # of the sensor grid, because slicing cannot read less than one chunk; at
    # 256 px each tile reads only the window it actually needs.
    src = cube.data
    if not isinstance(src, dsk.Array):
        src = dsk.from_array(src, chunks=(min(32, nb), 256, 256))
    src = src.rechunk({0: min(32, nb), 1: 256, 2: 256})
    bchunks = src.chunks[0]

    rows = []
    for i0 in range(0, ny, tile):
        i1 = min(i0 + tile, ny)
        row = []
        for j0 in range(0, nx, tile):
            j1 = min(j0 + tile, nx)
            th, tw = i1 - i0, j1 - j0
            keep = ~void_all[i0:i1, j0:j1]
            if not keep.any():        # tile lies entirely outside the strip
                row.append(dsk.full((nb, th, tw), np.nan, dtype="float32",
                                    chunks=(bchunks, th, tw)))
                continue
            ll = l_all[i0:i1, j0:j1]
            ss = s_all[i0:i1, j0:j1]
            y0, y1 = int(ll[keep].min()), int(ll[keep].max()) + 1
            x0, x1 = int(ss[keep].min()), int(ss[keep].max()) + 1
            # One spatial chunk per window so _gather can index across it;
            # the slice above is what keeps the read small.
            win = src[:, y0:y1, x0:x1].rechunk({1: -1, 2: -1})
            # Void cells clip to index 0, which falls outside the window once
            # it is rebased - park them on a valid pixel and let the mask blank
            # them, rather than letting a negative index blow up the gather.
            li = np.where(keep, ll - y0, 0)
            si = np.where(keep, ss - x0, 0)
            row.append(win.map_blocks(_gather, li, si, ~keep,
                                      dtype="float32",
                                      chunks=(win.chunks[0], th, tw)))
        rows.append(row)

    return xr.DataArray(dsk.block(rows), dims=("wavelength", "y", "x"),
                        coords={k: v for k, v in cube.coords.items()
                                if k not in ("y", "x")})


def _av5_cube_group(path: Path) -> str:
    """Name of the group holding the 3-D cube.

    AVIRIS-5 does not use one name for it: reflectance sits under
    ``reflectance/reflectance`` but its uncertainty sits under
    ``uncertainty/uncertainty``, so the group is looked up rather than guessed.
    """
    import h5py

    with h5py.File(path, "r") as h:
        for name, obj in h.items():
            if isinstance(obj, h5py.Group) and any(
                    getattr(d, "ndim", 0) == 3 for d in obj.values()):
                return name
    raise ValueError(f"no 3-D cube group in {path.name}")


def _av5_grid(cube: Path) -> tuple[str, tuple]:
    """CRS and GDAL-order transform from the ``transverse_mercator`` variable."""
    import rasterio.crs

    g = xr.open_dataset(cube)
    tm = g["transverse_mercator"].attrs
    crs = rasterio.crs.CRS.from_wkt(_as_str(tm.get("crs_wkt") or tm["spatial_ref"]))
    gt = tuple(float(v) for v in _as_str(tm["GeoTransform"]).split())
    g.close()
    return f"EPSG:{crs.to_epsg()}" if crs.to_epsg() else crs.to_wkt(), gt


def _as_str(v) -> str:
    return v.decode() if isinstance(v, bytes) else str(v)


def _apply_glt(raw: np.ndarray, sample: np.ndarray, line: np.ndarray) -> np.ndarray:
    """Put a raw ``(line, sample)`` layer onto the ortho grid.

    JPL's lookup tables are 1-based with 0 for "no data", and a negative index
    marks a cell filled from a neighbour rather than sampled directly. Both
    signs point at a real pixel, so only the zeros are dropped.
    """
    s = np.abs(sample).astype(np.int64) - 1
    ln = np.abs(line).astype(np.int64) - 1
    valid = (sample != 0) & (line != 0)
    out = np.full(sample.shape, np.nan, dtype="float32")
    np.clip(s, 0, raw.shape[1] - 1, out=s)
    np.clip(ln, 0, raw.shape[0] - 1, out=ln)
    out[valid] = raw[ln[valid], s[valid]]
    return out


# --- shared trimmings ----------------------------------------------------


def _finish(ds: xr.Dataset, var: str, units: str, product: str) -> None:
    """Coordinate metadata and the 1-D x/y every reader in the package sets."""
    ds["wavelength"].attrs.update(units="nm", long_name="band centre")
    if "fwhm" in ds.coords:
        ds["fwhm"].attrs.update(units="nm", long_name="band width")
    ds[var].attrs.update(
        units=units,
        long_name=("surface reflectance" if product == "reflectance"
                   else "at-sensor radiance"),
    )
    gt = ds.attrs.get("transform")
    if gt is None:
        # A sensor-grid cube (AVIRIS-5 L1B with ortho=False) has no mapping to
        # projected coordinates, so leaving y/x as plain indices is the honest
        # answer - inventing a transform would let to_geotiff write a file that
        # looks georeferenced and is not.
        return
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    ds.coords["x"] = ("x", gt[0] + (np.arange(nx) + 0.5) * gt[1])
    ds.coords["y"] = ("y", gt[3] + (np.arange(ny) + 0.5) * gt[5])
    note = ("" if not ds.attrs.get("rotation_deg") else
            " along the top row / left column only - the grid is rotated "
            f"{ds.attrs['rotation_deg']:g} deg, see attrs['transform']")
    ds["x"].attrs.update(units="m", standard_name="projection_x_coordinate",
                         long_name=f"easting{note}")
    ds["y"].attrs.update(units="m", standard_name="projection_y_coordinate",
                         long_name=f"northing{note}")


def _add_map_coords(ds: xr.Dataset) -> None:
    """Exact per-pixel easting/northing, which a rotated grid needs."""
    gt = ds.attrs["transform"]
    rows, cols = np.mgrid[0:ds.sizes["y"], 0:ds.sizes["x"]] + 0.5
    ds.coords["easting"] = (("y", "x"), gt[0] + gt[1] * cols + gt[2] * rows)
    ds.coords["northing"] = (("y", "x"), gt[3] + gt[4] * cols + gt[5] * rows)
    for name in ("easting", "northing"):
        ds[name].attrs.update(units="m", long_name=f"pixel-centre {name}")


def _blank_water_bands(ds: xr.Dataset) -> None:
    """NaN the water-vapour bands, keeping the band count.

    Uses the product's own ``bbl`` when it has one; AVIRIS-3 flags 35 of 284
    bands. Classic, NG and AVIRIS-5 ship no flag, so :data:`WATER_BANDS` stands
    in - the windows AVIRIS-3's list marks.
    """
    wl = ds["wavelength"].values
    if "good_wavelength" in ds.coords:
        bad = ~ds["good_wavelength"].values
    else:
        bad = np.zeros(wl.shape, bool)
        for lo, hi in WATER_BANDS:
            bad |= (wl >= lo) & (wl <= hi)
        ds.coords["good_wavelength"] = ("wavelength", ~bad)
    var = "reflectance" if "reflectance" in ds else "radiance"
    ds[var] = ds[var].where(xr.DataArray(~bad, dims="wavelength"))
    ds.attrs["good_bands_only"] = 1
    ds.attrs["bands_blanked"] = int(bad.sum())


def _add_geometry(ds: xr.Dataset, cube: Path, variant: _Variant,
                  granule: str, chunks) -> None:
    """Attach the OBS layers and derive the relative azimuth."""
    obs = _sibling(cube, granule, variant.obs)
    if obs is None:
        ds.attrs["obs_source"] = "none"
        warnings.warn(f"{granule}: no OBS file found near {cube.name} (looked for "
                      f"{', '.join(variant.obs)} in the cube's folder and its sibling folders); "
                      "geometry layers (sza, saa, vza, vaa, slope, aspect, cos_i, raa) not attached")
        return
    if variant.name == "AVIRIS-5":
        _add_geometry_av5(ds, obs)
    else:
        _add_geometry_envi(ds, obs, chunks)
    if "aspect" in ds:
        # AVIRIS-3 ships -180..180, AVIRIS-5 0..360; settle on one.
        ds["aspect"] = np.mod(ds["aspect"], 360.0).astype("float32")
        ds["aspect"].attrs.update(units="degrees",
                                  long_name="terrain aspect, cw from north")
    if "vaa" in ds and "saa" in ds:
        ds["raa"] = np.mod(ds["vaa"] - ds["saa"], 360.0).astype("float32")
        ds["raa"].attrs.update(units="degrees",
                               long_name="relative azimuth (VAA - SAA, mod 360)")
    ds.attrs["obs_source"] = obs.name


def _add_geometry_envi(ds: xr.Dataset, obs: Path, chunks) -> None:
    import rioxarray

    hdr = read_hdr(_hdr_for(obs))
    names = [n.strip().lower() for n in hdr.get("band names", "").split(",")]
    da = rioxarray.open_rasterio(
        obs, chunks=_chunks_for(obs, chunks, int(hdr.get("samples", 0) or 0),
                                int(hdr.get("bands", 0) or 0)), masked=False)
    if da.sizes["y"] != ds.sizes["y"] or da.sizes["x"] != ds.sizes["x"]:
        ds.attrs["obs_source"] = "none"
        warnings.warn(f"{obs.name}: OBS grid {da.sizes['y']}x{da.sizes['x']} does not match the cube "
                      f"{ds.sizes['y']}x{ds.sizes['x']}; geometry layers not attached")
        return
    attached = 0
    for i, name in enumerate(names):
        out = next((o for frag, o in OBS_BANDS if frag in name), None)
        if out is None or i >= da.sizes["band"]:
            continue
        layer = da.isel(band=i).astype("float32")
        ds[out] = (("y", "x"), layer.where(layer != FILL).data)
        units, long_name = OBS_UNITS[out]
        ds[out].attrs.update(units=units, long_name=long_name)
        attached += 1
    if not attached:
        ds.attrs["obs_source"] = "none"
        warnings.warn(f"{obs.name}: none of its band names ({', '.join(n for n in names if n)[:120]}) "
                      "match a known OBS layer; geometry layers not attached")


def _add_geometry_av5(ds: xr.Dataset, obs: Path) -> None:
    """AVIRIS-5 keeps OBS on the sensor grid; its own GLT puts it on the map."""
    import h5py

    with h5py.File(obs, "r") as h:
        if "geolocation_lookup_table" not in h:
            ds.attrs["obs_source"] = "none"
            warnings.warn(f"{obs.name}: no geolocation_lookup_table in the OBS file, so its "
                          "sensor-grid layers cannot be put on the map grid; geometry layers not attached")
            return
        sample = h["geolocation_lookup_table/sample"][:]
        line = h["geolocation_lookup_table/line"][:]
        shape = (ds.sizes["y"], ds.sizes["x"])
        if sample.shape != shape:
            probe = next((h[f"observation_parameters/{n}"] for n in AV5_OBS
                          if f"observation_parameters/{n}" in h), None)
            if probe is not None and probe.shape == shape:
                # The cube is on the sensor grid (ortho=False): the OBS layers
                # already share that grid, so attach them as they are.
                sample = line = None
            else:
                ds.attrs["obs_source"] = "none"
                warnings.warn(f"{obs.name}: OBS lookup table is {sample.shape[0]}x{sample.shape[1]} "
                              f"but the cube is {shape[0]}x{shape[1]}; geometry layers not attached")
                return
        for name, out in AV5_OBS.items():
            key = f"observation_parameters/{name}"
            if key not in h:
                continue
            raw = h[key][:].astype("float32")
            raw[raw == FILL] = np.nan
            ds[out] = (("y", "x"), raw if sample is None else _apply_glt(raw, sample, line))
            units, long_name = OBS_UNITS[out]
            ds[out].attrs.update(units=units, long_name=long_name)
        if "elev" in h:
            raw = h["elev"][:].astype("float32")
            raw[raw == FILL] = np.nan
            ds["elev"] = (("y", "x"), raw if sample is None else _apply_glt(raw, sample, line))
            ds["elev"].attrs.update(units="m", long_name="surface elevation")
            ds.attrs["elev_source"] = obs.name


@functools.lru_cache(maxsize=4)
def _elevation_array(src: str, band: int, glt: str | None, stamp: tuple,
                     ny: int, nx: int) -> np.ndarray | None:
    """Read (and if needed orthorectify) a DEM, remembering the last few.

    Reading it eagerly is what makes :func:`check_geometry` possible, but a
    notebook opens the same granule repeatedly and each open was re-reading
    0.2-0.5 GB and redoing the GLT gather. Four entries is 40-115 MB each
    depending on grid, so at most a few hundred MB held against opens that
    would otherwise cost seconds apiece.

    ``stamp`` is the source file's (mtime, size); it is in the key so an
    edited or replaced sidecar is not served from a stale entry.
    """
    import warnings

    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    with warnings.catch_warnings():
        # The raw loc/igm sidecars carry no geotransform - we want their
        # values, not their (absent) georeferencing, so the warning is noise.
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(src) as r:
            if band > r.count:
                return None
            z = r.read(band).astype("float32")
        z[z == FILL] = np.nan
        if z.shape == (ny, nx):
            return z
        if glt is None:
            return None
        with rasterio.open(glt) as g:
            smp, lin = g.read(1), g.read(2)   # band 1 sample, band 2 line
    if smp.shape != (ny, nx):
        return None
    return _apply_glt(z, smp, lin)


def _add_elevation(ds: xr.Dataset, cube: Path, variant: _Variant,
                   granule: str) -> None:
    """Attach a per-pixel DEM, orthorectifying it first if need be.

    Topographic correction needs elevation, and so does any honest check of the
    slope layer - which is the point: with a DEM in hand the slope convention
    can be *tested* rather than assumed per instrument.

    Only AVIRIS-3 delivers it already gridded (``LOC_ORT``). NG and Classic
    hand over the raw sensor grid (``loc``/``ort_igm``) plus a lookup table, so
    those get the same GLT treatment as AVIRIS-5's OBS.
    """
    if "elev" in ds:                       # AVIRIS-5 already has it
        return
    spec = ELEVATION.get(variant.name)
    if spec is None:
        return
    globs, band, glt_globs = spec
    src = _sibling(cube, granule, globs)
    if src is None:
        ds.attrs["elev_source"] = "none"
        warnings.warn(f"{granule}: no elevation source found (looked for {', '.join(globs)}); "
                      "'elev' not attached")
        return
    glt = _sibling(cube, granule, glt_globs) if glt_globs else None
    st = src.stat()
    z = _elevation_array(str(src), band, str(glt) if glt else None,
                         (st.st_mtime, st.st_size),
                         ds.sizes["y"], ds.sizes["x"])
    if z is None:
        ds.attrs['elev_source'] = 'none'
        warnings.warn(f"{granule}: elevation source {src.name} could not be mapped onto the cube grid (shape mismatch or unreadable); 'elev' not attached")
        return

    ds["elev"] = (("y", "x"), z.copy())
    ds["elev"].attrs.update(units="m", long_name="surface elevation")
    ds.attrs["elev_source"] = src.name


def _add_extras(ds: xr.Dataset, cube: Path, variant: _Variant,
                granule: str, chunks) -> None:
    """Atmospheric state: AOT and water vapour, however the variant ships it."""
    if variant.name == "AVIRIS-5":
        try:
            state = xr.open_dataset(cube, group="state_variables")
        except (OSError, KeyError):
            return
        rename = {"aerosol_optical_thickness": "aot", "water_vapor": "wv",
                  "carbon_dioxide": "co2"}
        for src, out in rename.items():
            if src in state:
                arr = state[src].values.astype("float32")
                arr[arr == FILL] = np.nan
                ds[out] = (("y", "x"), arr)
        state.close()
    else:
        atm = _sibling(cube, granule, variant.atm)
        if atm is None:
            return
        import rioxarray

        hdr = read_hdr(_hdr_for(atm))
        names = [n.strip().lower() for n in hdr.get("band names", "").split(",")]
        da = rioxarray.open_rasterio(
            atm, chunks=_chunks_for(atm, chunks, int(hdr.get("samples", 0) or 0),
                                    int(hdr.get("bands", 0) or 0)), masked=False)
        if da.sizes["y"] != ds.sizes["y"] or da.sizes["x"] != ds.sizes["x"]:
            return
        # AVIRIS-3 names its two bands; Classic's three-phase H2O file does not.
        default = (["aot", "wv"] if variant.name == "AVIRIS-3"
                   else ["wv", "liquid_water", "ice"])
        for i in range(da.sizes["band"]):
            name = names[i] if i < len(names) and names[i] else ""
            out = ({"aot550": "aot", "h2ostr": "wv"}.get(name)
                   or (default[i] if i < len(default) else f"atm_{i}"))
            layer = da.isel(band=i).astype("float32")
            ds[out] = (("y", "x"), layer.where(layer != FILL).data)
        ds.attrs["atm_source"] = atm.name

    for name, units, long_name in (
        ("aot", "1", "aerosol optical thickness at 550 nm"),
        ("wv", "cm", "column water vapour"),
        ("liquid_water", "cm", "column liquid water"),
        ("ice", "cm", "column ice"),
        ("co2", "ppm", "column carbon dioxide"),
    ):
        if name in ds:
            ds[name].attrs.update(units=units, long_name=long_name)


def _add_uncertainty(ds: xr.Dataset, cube: Path, variant: _Variant,
                     granule: str, chunks) -> None:
    unc = _sibling(cube, granule, variant.unc)
    if unc is None:
        return
    import rioxarray

    uhdr = read_hdr(_hdr_for(unc))
    da = rioxarray.open_rasterio(
        unc, chunks=_chunks_for(unc, chunks, int(uhdr.get("samples", 0) or 0),
                                int(uhdr.get("bands", 0) or 0)), masked=False)
    # The sidecar is always the full, file-order band set, while the cube may
    # have been subset by wl_range and reordered by sort_bands. band_index says
    # exactly which source band each cube band came from, so use that rather
    # than trying to match wavelengths back up.
    if "band_index" in ds.coords:
        idx = ds["band_index"].values
        if idx.max() < da.sizes["band"]:
            da = da.isel(band=idx)
    if da.sizes["band"] != ds.sizes["wavelength"]:
        raise ValueError(
            f"{unc.name} has {da.sizes['band']} bands but the cube has "
            f"{ds.sizes['wavelength']}; cannot line them up")
    arr = da.astype("float32").where(da != FILL)
    var = "reflectance" if "reflectance" in ds else "radiance"
    ds[f"{var}_uncertainty"] = (("y", "x", "wavelength"),
                                arr.transpose("y", "x", "band").data)
    ds[f"{var}_uncertainty"].attrs.update(
        units=ds.attrs["units"], long_name=f"posterior {var} uncertainty")
    ds.attrs["uncertainty_source"] = unc.name
