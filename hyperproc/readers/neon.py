"""NEON AOP reader - DP1.30006.001 flightline reflectance (NIS), HDF5.

NEON's Airborne Observation Platform flies the NEON Imaging Spectrometer
(an AVIRIS-NG-class instrument) over its ecological sites and delivers
orthorectified, atmospherically corrected (ATCOR) reflectance as one HDF5 file
per flightline, on a north-up 1 m UTM grid:

    NEON_D01_BART_DP1_20190825_145110_reflectance.h5
         ^   ^    ^   ^        ^
      domain site product date  flightline start (HHMMSS)

Everything lives under one site group - ``<SITE>/Reflectance/`` - with the
cube in ``Reflectance_Data`` as ``(line, sample, wavelength)`` int16 scaled by
10 000, and a rich ``Metadata/`` tree: 426 band centres and FWHM, the map
projection, per-pixel view angles, scalar solar angles for the line, and the
ATCOR inputs and outputs (slope, aspect, smoothed DEM, illumination, path
length, sky view, AOT, water vapour, haze/cloud/water and DDV class maps).

Five things to know, all checked against the BART 2019-08-25 lines here:

1. **The cube is already ``(y, x, wavelength)``.** No transpose, no GLT: NEON
   delivers a gridded product. The ``Interleave = BSQ`` attribute describes
   the *conceptual* layout, not the array order in the file.

2. **Some attribute labels are wrong, so values were checked, not trusted.**
   ``Smooth_Surface_Elevation`` is labelled "Average Solar Zenith Angle" in
   degrees; it holds elevation in metres (680-735 m at Bartlett).
   ``Illumination_Factor`` is labelled degrees; it is ``cos(i) x 100`` as
   uint8 - ``IF/100`` matches the incidence formula from slope, aspect and the
   solar angles at r = +0.9994, mean |diff| 0.0025, while cos(IF deg) is
   anti-correlated. ``Water_Vapor_Column`` has ``Scale_Factor = 1.0`` but its
   description says "[cm] x 1000", and 816 cm of water vapour is impossible
   where 0.816 cm is August in New Hampshire. The reader applies the scale the
   values demand and records each decision in the variable's ``note``.

3. **``Cast_Shadow`` does not hold the flag its description promises.** It
   documents ``1 = shadow, 0 = no shadow``; the line here holds only 1 and
   241, with 241 on the off-swath fill. It is exposed unmodified as
   ``cast_shadow_raw`` rather than given a meaning the data do not support.
   Use the ``hcw_class`` and ``ddv_class`` maps for shadow instead - both
   carry an explicit topographic-shadow class.

4. **Solar angles are one number per flightline**, not per pixel: ATCOR uses
   the line average. They are broadcast to ``(y, x)`` lazily so downstream code
   sees the same variables as for AVIRIS, and kept as scalar attrs too.

5. **Bad bands are the provider's.** ``Band_Window_1/2_Nanometers`` on the
   Reflectance group give NEON's own water-vapour windows (1340-1445 and
   1790-1955 nm here), and ``good_wavelength`` is built from them.

The cube is opened lazily through dask, chunked to the file's own gzip layout
``(336, 39, 14)`` in multiples, so a spatial window across all bands is a
handful of contiguous reads rather than a pass over 5 GB.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from hyperproc.readers._common import finish_bands, normalise_angles
import xarray as xr

from hyperproc.geometry import check_geometry, fix_slope_convention

FILL = -9999.0
SCALE = 10000.0

_GRANULE = re.compile(
    r"(?P<granule>NEON_(?P<domain>D\d{2})_(?P<site>[A-Z0-9]{4})_(?P<product>DP[13])"
    r"_(?P<date>\d{8})_(?P<time>\d{6}))")

#: Ancillary dataset -> (our name, scale to divide by, units, long name).
#: Scales follow the values, not the (sometimes wrong) attributes - see the
#: module docstring.
ANCILLARY = {
    "Slope": ("slope", 1.0, "degrees", "terrain slope from horizontal"),
    "Aspect": ("aspect", 1.0, "degrees", "terrain aspect, cw from north"),
    "Smooth_Surface_Elevation": ("elev", 1.0, "m", "smoothed surface elevation"),
    "Path_Length": ("path_length", 1.0, "m", "sensor-to-ground path length"),
    "Illumination_Factor": ("cos_i", 100.0, "1",
                            "cosine of the solar incidence angle on the slope"),
    "Sky_View_Factor": ("sky_view", 100.0, "1", "sky view factor"),
    "Aerosol_Optical_Depth": ("aot", 1000.0, "1", "aerosol optical thickness at 550 nm"),
    "Water_Vapor_Column": ("wv", 1000.0, "cm", "column water vapour"),
    "Visibility_Index_Map": ("visibility", 1.0, "km", "sea-level visibility"),
}

#: ATCOR writes its byte layers (Illumination_Factor, Sky_View_Factor,
#: Cast_Shadow, Visibility_Index_Map) with 241 outside the swath: the declared
#: Data_Ignore_Value of -9999 cannot be stored in a uint8. Checked on all 36
#: BART lines: 241 coincides exactly with the reflectance no-data footprint.
BYTE_NODATA = 241

#: Class maps, exposed as integer layers with their lookup tables as attrs.
CLASSES = {
    "Haze_Cloud_Water_Map": "hcw_class",
    "Dark_Dense_Vegetation_Classification": "ddv_class",
}

NOTES = {
    "elev": "file labels this 'Average Solar Zenith Angle' in degrees; values are metres",
    "cos_i": "file labels this 'degrees'; it is cos(i) x 100 (r=+0.9994 vs the incidence formula)",
    "wv": "file Scale_Factor is 1.0 but the description says [cm] x 1000; 0.8 cm, not 816",
    "aot": "Band_Names says 550 nm, Description says 500 nm; ATCOR reports 550",
}


def open_neon(
    path: str | Path,
    wl_range: tuple[float, float] | None = None,
    good_bands_only: bool = False,
    geometry: bool = True,
    extras: bool = True,
    classes: bool = True,
    fix_geometry: bool | str = "auto",
    chunks: str | tuple | None = "auto",
) -> xr.Dataset:
    """Open a NEON DP1.30006.001 flightline.

    Args:
        path: ``NEON_D??_SITE_DP1_YYYYMMDD_HHMMSS_reflectance.h5``.
        wl_range: ``(min_nm, max_nm)``, applied before any data is read.
        good_bands_only: NaN the bands inside NEON's own water-vapour windows
            (``Band_Window_1/2_Nanometers``), keeping the band count.
        geometry: attach ``slope``, ``aspect``, ``elev``, ``cos_i``,
            ``path_length``, per-pixel ``vza``/``vaa``, the line's scalar
            ``sza``/``saa`` broadcast to the grid, and a derived ``raa``.
        extras: attach ``aot``, ``wv``, ``sky_view``, ``visibility``.
        classes: attach ``hcw_class`` and ``ddv_class`` with their lookup
            tables, plus ``cast_shadow_raw``.
        fix_geometry: ``"auto"`` runs :func:`hyperproc.check_geometry` against
            the shipped DEM and corrects slope/``cos_i`` only if the product
            stores slope from vertical (NEON does not, on the lines here -
            the verdict lands in ``attrs["geometry_check"]``). ``True``
            forces it, ``False`` leaves every layer as delivered.
        chunks: dask chunking. ``"auto"`` aligns to the file's gzip chunks
            with all bands together; ``None`` reads eagerly.

    Returns:
        ``xarray.Dataset`` with ``reflectance(y, x, wavelength)`` in 0-1,
        ``wavelength``/``fwhm``/``good_wavelength`` coordinates, and
        ``attrs["transform"]`` in GDAL order on a north-up UTM grid.
    """
    import h5py

    path = Path(path)
    m = _GRANULE.search(path.name)
    if not m:
        raise ValueError(
            f"{path.name!r} is not a NEON AOP reflectance file. Expected e.g. "
            f"NEON_D01_BART_DP1_20190825_145110_reflectance.h5")
    granule = m.group("granule")
    if m.group("product") != "DP1":
        raise NotImplementedError(
            f"{m.group('product')} is not supported yet - only DP1 flightlines. "
            f"DP3 mosaic tiles carry a Data_Selection_Index and per-tile "
            f"solar-angle logs that need their own handling.")

    h = h5py.File(path, "r")          # metadata only; closed before returning (see _H5Array)
    site = m.group("site")
    if site not in h:
        site = next(k for k in h if isinstance(h[k], h5py.Group))
    refl = h[f"{site}/Reflectance"]
    meta = refl["Metadata"]
    dset = refl["Reflectance_Data"]

    wl = meta["Spectral_Data/Wavelength"][()].astype("float64")
    fwhm = meta["Spectral_Data/FWHM"][()].astype("float64")
    keep = _band_subset(wl, wl_range)

    good, windows = _good_bands(wl, refl.attrs)
    if keep is not None:
        wl, fwhm, good = wl[keep], fwhm[keep], good[keep]

    cube = _lazy_cube(dset, chunks)
    if keep is not None:
        cube = cube[:, :, keep]
    nodata = float(dset.attrs.get("Data_Ignore_Value", FILL))
    scale = float(dset.attrs.get("Scale_Factor", SCALE))
    arr = (cube.astype("float32") / np.float32(scale))
    import dask.array as dsk
    arr = dsk.where(cube != nodata, arr, np.float32(np.nan))

    ds = xr.Dataset(
        {"reflectance": (("y", "x", "wavelength"), arr)},
        coords={"wavelength": ("wavelength", wl),
                "fwhm": ("wavelength", fwhm),
                "good_wavelength": ("wavelength", good),
                "band_index": ("wavelength", keep if keep is not None
                               else np.arange(wl.size))},
    )
    ds["wavelength"].attrs.update(units="nm", long_name="band centre")
    ds["fwhm"].attrs.update(units="nm", long_name="band width")
    ds["good_wavelength"].attrs["long_name"] = (
        "usable band (provider Band_Window_*_Nanometers)")
    ds["band_index"].attrs["long_name"] = "0-based band position in the source file"
    ds["reflectance"].attrs.update(units="1", long_name="surface reflectance (ATCOR)")

    epsg, transform = _grid(meta, dset)
    acq = str(refl.attrs.get("Acquisition_Time", ""))
    ds.attrs.update(
        sensor="NEON", instrument=_as_str(refl.attrs.get("Sensor", "NIS")),
        level="L1", product="reflectance", units="1", orthorectified=1,
        granule=granule, stem=granule, site=site, domain=m.group("domain"),
        datetime=f"{m.group('date')[:4]}-{m.group('date')[4:6]}-{m.group('date')[6:]}"
                 f"T{m.group('time')[:2]}:{m.group('time')[2:4]}:{m.group('time')[4:]}",
        acquisition_time=acq, crs=f"EPSG:{epsg}", transform=transform,
        rotation_deg=0.0, fill_value=nodata, scale_factor=scale,
        good_bands_source="provider band windows",
        bad_band_windows_nm=windows, source=path.name,
        sza=float(meta["Logs/Solar_Zenith_Angle"][()]),
        saa=float(meta["Logs/Solar_Azimuth_Angle"][()]),
        cloud_conditions=_as_str(dset.attrs.get("Cloud conditions", "")),
    )
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    ds.coords["x"] = ("x", transform[0] + (np.arange(nx) + 0.5) * transform[1])
    ds.coords["y"] = ("y", transform[3] + (np.arange(ny) + 0.5) * transform[5])
    ds["x"].attrs.update(units="m", standard_name="projection_x_coordinate")
    ds["y"].attrs.update(units="m", standard_name="projection_y_coordinate")

    if geometry:
        _add_geometry(ds, meta, chunks)
        if fix_geometry:
            report = (check_geometry(ds) if fix_geometry == "auto"
                      else {"needs_fix": True, "evidence": "fix_geometry=True",
                            "convention": "vertical"})
            ds.attrs["geometry_check"] = report.get("evidence", "")
            ds.attrs["slope_convention"] = report.get("convention", "horizontal")
            if report["needs_fix"]:
                fix_slope_convention(ds)
    if extras:
        _add_layers(ds, meta["Ancillary_Imagery"],
                    ("Aerosol_Optical_Depth", "Water_Vapor_Column",
                     "Sky_View_Factor", "Visibility_Index_Map"), chunks)
    if classes:
        _add_classes(ds, meta["Ancillary_Imagery"], chunks)
    if good_bands_only:
        bad = ~ds["good_wavelength"].values
        ds["reflectance"] = ds["reflectance"].where(
            xr.DataArray(~bad, dims="wavelength"))
        ds.attrs["good_bands_only"] = 1
        ds.attrs["bands_blanked"] = int(bad.sum())
    finish_bands(ds)
    normalise_angles(ds)
    h.close()
    return ds


# --- pieces --------------------------------------------------------------


def _as_str(v) -> str:
    return v.decode() if isinstance(v, bytes) else str(v)


def _band_subset(wl: np.ndarray, wl_range) -> np.ndarray | None:
    if wl_range is None:
        return None
    lo, hi = wl_range
    keep = np.where((wl >= lo) & (wl <= hi))[0]
    if keep.size == 0:
        raise ValueError(f"no bands in {wl_range} nm; this line covers "
                         f"{wl.min():.1f}-{wl.max():.1f} nm")
    return keep


def _good_bands(wl: np.ndarray, attrs) -> tuple[np.ndarray, list]:
    """NEON's own bad-band windows, from ``Band_Window_N_Nanometers``."""
    windows = []
    for k in sorted(k for k in attrs if k.startswith("Band_Window_")):
        lo, hi = (float(v) for v in np.asarray(attrs[k]).ravel()[:2])
        windows.append((lo, hi))
    bad = np.zeros(wl.shape, bool)
    for lo, hi in windows:
        bad |= (wl >= lo) & (wl <= hi)
    return ~bad, [list(w) for w in windows]


def _grid(meta, dset) -> tuple[int, tuple]:
    """EPSG and GDAL-order transform from Map_Info, cross-checked to the extent.

    Map_Info is ``proj, refx, refy, easting, northing, px, py, zone, hemi,
    datum, units, rotation``; the easting/northing are the upper-left *edge*,
    which the Spatial_Extent attribute confirms (extent width / px = samples).
    """
    epsg = int(_as_str(meta["Coordinate_System/EPSG Code"][()]))
    parts = [p.strip() for p in _as_str(meta["Coordinate_System/Map_Info"][()]).split(",")]
    x0, y0, px, py = (float(parts[i]) for i in (3, 4, 5, 6))
    rot = float(parts[-1].split("=")[-1]) if parts else 0.0
    if rot:
        raise NotImplementedError(f"rotated Map_Info ({rot} deg) not handled for NEON")
    ext = dset.attrs.get("Spatial_Extent_meters")
    if ext is not None:
        ext = np.asarray(ext, dtype="float64")
        nx_ext, ny_ext = (ext[1] - ext[0]) / px, (ext[3] - ext[2]) / py
        if not (abs(nx_ext - dset.shape[1]) < 1 and abs(ny_ext - dset.shape[0]) < 1):
            raise ValueError(f"Map_Info pixel size disagrees with Spatial_Extent "
                             f"({nx_ext:.0f}x{ny_ext:.0f} vs {dset.shape[1]}x{dset.shape[0]})")
    return epsg, (x0, px, 0.0, y0, 0.0, -py)


class _H5Array:
    """Array-like view of one HDF5 dataset that reopens the file for every
    read. The dask graph then holds only a path and a dataset name: it can be
    pickled (distributed / process schedulers), and no file handle is left
    open after ``hyperproc.open`` returns."""

    def __init__(self, dset):
        self.path, self.name = dset.file.filename, dset.name
        self.shape, self.dtype, self.ndim = dset.shape, dset.dtype, dset.ndim
        self.chunks = dset.chunks

    def __getitem__(self, key):
        import h5py
        with h5py.File(self.path, "r") as h:
            return h[self.name][key]


def _chunks_for(dset, spec):
    """Dask chunks: whole rows of the file's gzip chunk height, all bands.

    Full-width rows make every chunk a complete GeoTIFF strip (the writer
    otherwise rewrites each strip once per x-chunk) and read each gzip chunk
    exactly once.
    """
    if spec != "auto":
        return spec
    cy = (dset.chunks or (27, dset.shape[1], dset.shape[2]))[0]
    return (cy, dset.shape[1], dset.shape[2])


def _lazy_cube(dset, chunks):
    import dask.array as dsk

    if chunks is None:
        return dsk.from_array(dset[()], chunks=-1)
    return dsk.from_array(_H5Array(dset), chunks=_chunks_for(dset, chunks), lock=False)


def _lazy_layer(dset, chunks):
    import dask.array as dsk

    if chunks is None:
        return dsk.from_array(dset[()], chunks=-1)
    cy = (dset.chunks or (27, dset.shape[1]))[0]
    return dsk.from_array(_H5Array(dset), chunks=(cy * 8, dset.shape[1]), lock=False)


def _scaled(dset, scale, chunks):
    """Float layer with the file's ignore value as NaN, divided by ``scale``."""
    import dask.array as dsk

    raw = _lazy_layer(dset, chunks)
    ign = dset.attrs.get("Data_Ignore_Value")
    out = raw.astype("float32") / np.float32(scale)
    if ign is not None and np.issubdtype(raw.dtype, np.integer) and raw.dtype.kind == "u":
        # Unsigned layers cannot hold -9999; ATCOR uses 241 instead. Without
        # this, cos_i reads 2.41 and sky_view 2.41 on every off-swath pixel.
        return dsk.where(raw != BYTE_NODATA, out, np.float32(np.nan))
    if ign is not None:
        out = dsk.where(raw != float(ign), out, np.float32(np.nan))
    return out


def _add_layers(ds, anc, names, chunks) -> None:
    for name in names:
        if name not in anc or name not in ANCILLARY:
            continue
        out, scale, units, long = ANCILLARY[name]
        ds[out] = (("y", "x"), _scaled(anc[name], scale, chunks))
        ds[out].attrs.update(units=units, long_name=long, source=name)
        if out in NOTES:
            ds[out].attrs["note"] = NOTES[out]


def _add_geometry(ds, meta, chunks) -> None:
    import dask.array as dsk

    anc = meta["Ancillary_Imagery"]
    _add_layers(ds, anc, ("Slope", "Aspect", "Smooth_Surface_Elevation",
                          "Path_Length", "Illumination_Factor"), chunks)
    for src, out in (("to-sensor_Zenith_Angle", "vza"), ("to-sensor_Azimuth_Angle", "vaa")):
        if src in meta:
            ds[out] = (("y", "x"), _scaled(meta[src], 1.0, chunks))
            ds[out].attrs.update(units="degrees",
                                 long_name=("to-sensor zenith" if out == "vza"
                                            else "to-sensor azimuth, cw from north"))
    ny, nx = ds.sizes["y"], ds.sizes["x"]
    ch = ds["reflectance"].data.chunks[:2] if hasattr(ds["reflectance"].data, "chunks") else (ny, nx)
    for key, out, long in (("Solar_Zenith_Angle", "sza", "to-sun zenith"),
                           ("Solar_Azimuth_Angle", "saa", "to-sun azimuth, cw from north")):
        v = float(meta["Logs"][key][()])
        ds[out] = (("y", "x"), dsk.full((ny, nx), np.float32(v), chunks=ch, dtype="float32"))
        ds[out].attrs.update(units="degrees", long_name=long,
                             note="one value per flightline (ATCOR line average), broadcast")
    if "vaa" in ds and "saa" in ds:
        ds["raa"] = np.mod(ds["vaa"] - ds["saa"], 360.0).astype("float32")
        ds["raa"].attrs.update(units="degrees",
                               long_name="relative azimuth (VAA - SAA, mod 360)")


def _add_classes(ds, anc, chunks) -> None:
    for src, out in CLASSES.items():
        if src not in anc:
            continue
        ds[out] = (("y", "x"), _lazy_layer(anc[src], chunks))
        names = [_as_str(n) for n in np.asarray(anc[src].attrs.get("Class_Names", []))]
        ds[out].attrs.update(long_name=_as_str(anc[src].attrs.get("Description", src)),
                             classes=names, nodata=int(anc[src].attrs.get("Data_Ignore_Value", 0)))
    if "Cast_Shadow" in anc:
        ds["cast_shadow_raw"] = (("y", "x"), _lazy_layer(anc["Cast_Shadow"], chunks))
        ds["cast_shadow_raw"].attrs.update(
            long_name="Cast_Shadow, unmodified",
            file_says=_as_str(anc["Cast_Shadow"].attrs.get("Units", "")),
            note="documented as 0/1 but holds 1 and 241 on the lines seen; 241 is the "
                 "off-swath fill. Use hcw_class 21 / ddv_class 4 for topographic shadow.")
