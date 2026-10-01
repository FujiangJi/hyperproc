"""Writing cubes back out to disk."""

from __future__ import annotations

import warnings

from pathlib import Path

import numpy as np
import xarray as xr

#: Variables a reader may produce as the main cube, in preference order.
_CUBE_VARS = ("reflectance", "radiance")


def main_var(ds: xr.Dataset) -> str:
    """Name of the dataset's cube variable (``reflectance`` or ``radiance``)."""
    for v in _CUBE_VARS:
        if v in ds:
            return v
    spectral = [v for v in ds.data_vars if "wavelength" in ds[v].dims]
    if spectral:
        return spectral[0]
    raise ValueError(f"no spectral cube found in {list(ds.data_vars)}")


def default_name(ds: xr.Dataset, suffix: str = "", ext: str = ".tif") -> str:
    """``<stem><suffix><ext>`` - the source filename with .nc swapped out.

    Most sensors carry the level in the granule id already
    (``EMIT_L2A_RFL_...``), so ``granule`` is enough to name a file uniquely.
    AVIRIS ids do not - ``AV320231005t181518`` is the flight line, shared by
    L1B and L2A - and the two levels do not always agree: AVIRIS-3 ships a
    ``bbl`` on L2A and none on L1B, so their band tables genuinely differ.
    Readers in that position set ``attrs["stem"]`` to disambiguate rather than
    let the second write silently replace the first.
    """
    stem = (ds.attrs.get("stem") or ds.attrs.get("granule")
            or f"{ds.attrs.get('sensor', 'cube')}")
    return f"{stem}{suffix}{ext}"


def _resolve(path: str | Path, ds: xr.Dataset, suffix: str = "",
             ext: str = ".tif") -> Path:
    """Accept either a full file path or a directory to name the file inside."""
    path = Path(path)
    if path.is_dir() or not path.suffix:
        path = path / default_name(ds, suffix, ext)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path



def _transform_for(ds: xr.Dataset):
    """The affine to write, rebuilt from the dataset's own x/y coordinates.

    ``attrs["transform"]`` describes the granule as delivered, so it goes stale
    the moment anyone subsets. rioxarray normally sidesteps that by deriving
    the affine from the coordinates - but it cannot for the flight-aligned
    AVIRIS grids, where rotation makes easting depend on the row as well as the
    column, and it falls back to a north-up transform that puts the image in
    the wrong place.

    So: take the rotation and pixel size from ``attrs["transform"]``, and
    recover the origin from where the coordinates actually start. The 1-D
    ``x``/``y`` are written as ``gt[0] + (col + 0.5) * gt[1]`` and
    ``gt[3] + (row + 0.5) * gt[5]``, so inverting them gives the subset's
    offset exactly, and their spacing gives any stride.

    Returns None when there is nothing better than rioxarray's own guess.
    """
    from affine import Affine

    gt = ds.attrs.get("transform")
    if not gt or "x" not in ds.coords or "y" not in ds.coords:
        return None
    gt = [float(v) for v in gt]
    if not (gt[1] and gt[5]):
        return None
    x, y = np.atleast_1d(ds["x"].values), np.atleast_1d(ds["y"].values)

    sx = (x[1] - x[0]) / gt[1] if x.size > 1 else 1.0
    sy = (y[1] - y[0]) / gt[5] if y.size > 1 else 1.0
    col0 = (x[0] - gt[0]) / gt[1] - 0.5
    row0 = (y[0] - gt[3]) / gt[5] - 0.5
    return Affine.from_gdal(
        gt[0] + col0 * gt[1] + row0 * gt[2], gt[1] * sx, gt[2] * sy,
        gt[3] + col0 * gt[4] + row0 * gt[5], gt[4] * sx, gt[5] * sy,
    )


#: Output formats, and the extension each uses when naming a file for you.
FORMATS = {"GTiff": ".tif", "ENVI": ".img"}

#: ENVI interleaves. BIL is the hyperspectral norm and matches how the readers stream.
INTERLEAVES = ("bil", "bip", "bsq")


def envi_header(ds: xr.Dataset, var: str | None = None) -> dict:
    """The spectral fields an ENVI header carries and a GeoTIFF cannot.

    A GeoTIFF can only label a band with free text, so ``650.4 nm`` is a
    description a human reads. An ENVI header states ``wavelength``, ``fwhm``
    and ``bbl`` as fields that ENVI, Spectronon and this package's own readers
    parse back into numbers. That is the reason to write ENVI at all.

    ``bbl`` follows ENVI's convention: 1 for a usable band, 0 for one to
    ignore, taken from ``good_wavelength``. Exporting a bad-band list is
    something the GeoTIFF route cannot do.
    """
    out = {}
    if "wavelength" not in ds.coords:
        return out
    wl = np.asarray(ds["wavelength"].values, dtype="float64")
    # 10 significant digits: enough to carry a float32 band centre exactly.
    # Six, the obvious choice, rounds EMIT's 381.0055847 to 381.006 and loses
    # 5e-3 nm, which is small but avoidable and would be silently baked in.
    out["wavelength"] = "{" + ", ".join(f"{v:.10g}" for v in wl) + "}"
    out["wavelength units"] = "Nanometers"
    if "fwhm" in ds.coords:
        fwhm = np.asarray(ds["fwhm"].values, dtype="float64")
        if fwhm.shape == wl.shape and np.isfinite(fwhm).any():
            out["fwhm"] = "{" + ", ".join(f"{v:.10g}" for v in fwhm) + "}"
    if "good_wavelength" in ds.coords:
        good = np.asarray(ds["good_wavelength"].values).astype(bool)
        if good.shape == wl.shape:
            out["bbl"] = "{" + ", ".join("1" if g else "0" for g in good) + "}"
    return out


def _write_cube(ds: xr.Dataset, path, var, driver: str, compress, overviews,
                overview_resampling: str, interleave: str | None) -> Path:
    """Shared writer for every format: CRS, streaming, band labels, metadata.

    The streaming rules here were expensive to find and are format independent,
    so both writers use them rather than keeping two copies that drift.
    """
    import rioxarray  # noqa: F401  registers the .rio accessor

    if driver not in FORMATS:
        raise ValueError(f"format must be one of {sorted(FORMATS)}; got {driver!r}")
    if "crs" not in ds.attrs:
        raise ValueError(
            "dataset has no CRS. Either re-open with ortho=True (EMIT), or, for "
            "a lat/lon swath such as PRISMA L2B/L2C or PACE, project it first:\n"
            "    ds = hyperproc.georeference(ds)   # -> UTM grid\n"
            "    hyperproc.to_geotiff(ds, out_dir)"
        )

    var = var or main_var(ds)
    path = _resolve(path, ds, ext=FORMATS[driver])

    da = ds[var].transpose("wavelength", "y", "x")
    da = da.rio.write_crs(ds.attrs["crs"]).rio.write_nodata(np.nan, encoded=False)
    affine = _transform_for(ds)
    if affine is not None:
        da = da.rio.write_transform(affine)

    if driver == "GTiff":
        kw = {"compress": compress} if compress else {}
        # Classic TIFF caps at 4 GB. Deflate usually keeps a full 285-band cube
        # under that, but an uncompressed one is ~5 GB, so let GDAL switch formats
        # rather than fail near the end of a multi-minute write.
        kw["BIGTIFF"] = "IF_SAFER"
        # Band-interleaved output: a single band of a 400-band cube can be read
        # without touching the other 399 (quicklooks, ratio checks, GIS band
        # browsing); compression runs on all cores instead of one.
        kw.update(interleave="band", NUM_THREADS="ALL_CPUS")
    else:
        # ENVI is a flat binary: no compression, no 4 GB limit, no internal
        # pyramids. A full EMIT cube is 5.1 GB here against 2.2 GB deflated.
        kw = {"driver": "ENVI", "INTERLEAVE": (interleave or "bil").upper()}

    if getattr(da.data, "chunks", None) is not None:
        # Dask-backed: STREAM. Without a lock rioxarray materialises the whole
        # array (28-33 GB for one AVIRIS-3 line) before writing; with one it
        # hands the chunks to dask.array.store one at a time.
        #
        # Each chunk must be a whole strip: full width, all bands. A cube
        # chunked in tiles or band groups (EMIT 512x512x32, NEON x split in 8,
        # AVIRIS-5 netCDF 256x256x10) would otherwise write every compressed
        # strip once per tile column and band group - 45 partial writes for
        # EMIT, 645 for AVIRIS-5 - and GDAL appends each rewritten strip, so
        # the file fills with dead space (an EMIT export grew from 2.1 to
        # 4.7 GB). Strips are ~256 MB, made of whole source row-chunks where
        # those are smaller.
        import threading
        nb, ny, nx = da.shape
        per_row = max(1, nx * nb * da.dtype.itemsize)
        rows = int(max(1, min(ny, 256e6 // per_row)))
        src_rows = int(max(da.data.chunks[1]))
        if src_rows < rows:
            rows = max(src_rows, (rows // src_rows) * src_rows)
        da = da.chunk({da.dims[0]: -1, da.dims[1]: rows, da.dims[2]: -1})
        if driver == "GTiff":
            kw.update(tiled=False, blockysize=rows)
        da.rio.to_raster(path, lock=threading.Lock(), **kw)
    else:
        if driver == "GTiff":
            kw.update(tiled=True)
        da.rio.to_raster(path, **kw)

    # Label each band with its wavelength; rioxarray does not do this itself.
    import rasterio

    with rasterio.open(path, "r+") as dst:
        for i, wl in enumerate(ds["wavelength"].values, start=1):
            dst.set_band_description(i, f"{wl:.1f} nm")
        dst.update_tags(
            sensor=ds.attrs.get("sensor", ""),
            level=ds.attrs.get("level", ""),
            granule=ds.attrs.get("granule", ""),
            datetime=ds.attrs.get("datetime", ""),
            units=ds.attrs.get("units", ""),
            variable=var,
        )
        if driver == "ENVI":
            # Also put the scene metadata in the .hdr. Written to the default
            # domain it lands in a GDAL-only .aux.xml sidecar, which ENVI does
            # not read, so the header would say less than the GeoTIFF did.
            fields = envi_header(ds, var)
            for key in ("sensor", "level", "granule", "datetime", "units"):
                if ds.attrs.get(key):
                    fields[key] = str(ds.attrs[key])
            fields["variable"] = var
            if fields:
                dst.update_tags(ns="ENVI", **fields)
    if overviews:
        if driver == "ENVI":
            warnings.warn("ENVI has no internal pyramids; overviews were not built. "
                          "Write GeoTIFF, or build external .ovr files yourself.",
                          stacklevel=3)
        else:
            build_overviews(path, None if overviews is True else overviews,
                            resampling=overview_resampling, compress=compress)
    return path


def to_geotiff(
    ds: xr.Dataset,
    path: str | Path,
    var: str | None = None,
    compress: str = "deflate",
    overviews: bool | list[int] | None = None,
    overview_resampling: str = "average",
) -> Path:
    """Write a cube to a multi-band GeoTIFF, one band per wavelength.

    Band descriptions are set to the wavelength in nm, so QGIS and ArcGIS show
    ``650.4 nm`` rather than ``Band 12``. With ``overviews`` the file also gets
    internal pyramids (what QGIS's *Build Overviews* does), so a GIS can draw the
    whole cube without reading it at full resolution.

    For a header that states the wavelengths as numbers rather than as band
    labels, and that can carry a bad-band list, see :func:`to_envi`.

    Args:
        ds: dataset from :func:`hyperproc.open`. Must be orthorectified -
            a sensor-grid cube has no CRS to write.
        path: output ``.tif``, or a **directory**, in which case the file is
            named after the source granule - ``EMIT_L2A_RFL_..._002.nc``
            becomes ``EMIT_L2A_RFL_..._002.tif``. Parents are created.
        var: which variable to write. Defaults to the cube variable.
        compress: GeoTIFF compression. ``"deflate"`` is lossless and roughly
            halves the file; pass ``None`` for none.
        overviews: ``True`` builds internal overview pyramids with factors
            2, 4, 8, ... until the coarsest level is under 256 px; a list gives
            the factors explicitly (``[2, 4, 8, 16]``); ``None`` (default)
            builds none. See :func:`build_overviews`.
        overview_resampling: how overview pixels are computed - ``"average"``
            (default, right for reflectance), ``"nearest"``, ``"bilinear"``,
            ``"cubic"``, ``"mode"`` ...

    Returns:
        The path written.

    Raises:
        ValueError: the dataset is on the sensor grid and has no CRS.
    """
    return _write_cube(ds, path, var, "GTiff", compress, overviews,
                       overview_resampling, None)


def to_envi(
    ds: xr.Dataset,
    path: str | Path,
    var: str | None = None,
    interleave: str = "bil",
) -> Path:
    """Write a cube to an ENVI flat binary with its ``.hdr``.

    The reason to choose this over :func:`to_geotiff` is the header. It states
    ``wavelength``, ``fwhm`` and ``bbl`` as fields, so ENVI, Spectronon and this
    package's own readers recover the band centres, widths and bad-band list as
    numbers. A GeoTIFF can only carry them as band labels, and cannot carry a
    bad-band list at all.

    The costs are real. ENVI has no compression, so a full EMIT product is
    about 5.1 GB here against 2.2 GB as a deflated GeoTIFF, and it has no
    internal pyramids, so a GIS redraws from full resolution.

    Args:
        ds: dataset from :func:`hyperproc.open`, orthorectified.
        path: output ``.img``, or a directory to name the file inside. GDAL
            writes the header beside it as ``<stem>.hdr``.
        var: which variable to write. Defaults to the cube variable.
        interleave: ``"bil"`` (default), ``"bip"`` or ``"bsq"``.

    Returns:
        The path of the binary. The header is ``<stem>.hdr`` beside it.

    Raises:
        ValueError: no CRS, or an unknown interleave.
    """
    if str(interleave).lower() not in INTERLEAVES:
        raise ValueError(f"interleave must be one of {INTERLEAVES}; got {interleave!r}")
    return _write_cube(ds, path, var, "ENVI", None, None, "average", str(interleave).lower())


def to_raster(ds: xr.Dataset, path: str | Path, format: str = "GTiff", **kwargs) -> Path:
    """Write a cube in either format. ``format`` is ``"GTiff"`` or ``"ENVI"``.

    A single door for code that takes the format as a setting; the keyword
    arguments are those of :func:`to_geotiff` or :func:`to_envi`.
    """
    if format not in FORMATS:
        raise ValueError(f"format must be one of {sorted(FORMATS)}; got {format!r}")
    return (to_envi if format == "ENVI" else to_geotiff)(ds, path, **kwargs)


def build_overviews(
    path: str | Path,
    factors: list[int] | None = None,
    resampling: str = "average",
    compress: str | None = "deflate",
    min_size: int = 256,
) -> list[int]:
    """Add internal overview pyramids to an existing GeoTIFF.

    This is what QGIS's *Raster > Miscellaneous > Build Overviews (Pyramids)*
    and ``gdaladdo`` do: reduced-resolution copies of every band are appended
    to the file so a viewer can draw it zoomed out without decoding the full
    cube. The pyramids are compressed like the main image, band-interleaved,
    and built on all cores. Nodata (NaN) pixels are left out of the averages.

    Args:
        path: GeoTIFF to modify in place (the main image is untouched).
        factors: reduction factors, e.g. ``[2, 4, 8, 16]``. Default: powers of
            two while the coarsest level is still at least ``min_size`` px on
            its longer side.
        resampling: any :class:`rasterio.enums.Resampling` name.
        compress: compression for the overview levels; ``None`` for none.
        min_size: stops the default factor list.

    Returns:
        The factors built (empty if the image is already smaller than
        ``min_size``). Size cost is roughly a third of the main image before
        compression; reading the overviews of band 1 back is
        ``rasterio.open(path).overviews(1)``.
    """
    import rasterio
    from rasterio.enums import Resampling

    path = Path(path)
    with rasterio.open(path) as src:
        longest = max(src.width, src.height)
    if factors is None:
        factors, f = [], 2
        while longest / f >= min_size:
            factors.append(f)
            f *= 2
    factors = [int(f) for f in factors]
    if not factors:
        return []
    env = {
        "COMPRESS_OVERVIEW": compress.upper() if compress else "NONE",
        "INTERLEAVE_OVERVIEW": "BAND",
        "BIGTIFF_OVERVIEW": "IF_SAFER",
        "GDAL_TIFF_OVR_BLOCKSIZE": "256",
        "GDAL_NUM_THREADS": "ALL_CPUS",
    }
    with rasterio.Env(**env), rasterio.open(path, "r+") as dst:
        dst.build_overviews(factors, Resampling[resampling])
        dst.update_tags(ns="rio_overview", resampling=resampling)
    return factors


def to_geotiff_2d(ds: xr.Dataset, path: str | Path, var: str,
                  overviews: bool | list[int] | None = None, overview_resampling: str = "average",
                  tags: dict | None = None, format: str = "GTiff") -> Path:
    """Write a single 2-D layer (``sza``, ``elev``, ``cloud``, ...) to GeoTIFF.

    ``path`` may be a directory, in which case the file is named
    ``<granule>_<var>.tif``. ``tags`` are written as GeoTIFF metadata, which is
    how a flag layer carries its own bit meanings.
    """
    import rioxarray  # noqa: F401

    if "crs" not in ds.attrs:
        raise ValueError(
            "dataset has no CRS. Either re-open with ortho=True (EMIT), or, for "
            "a lat/lon swath such as PRISMA L2B/L2C or PACE, project it first:\n"
            "    ds = hyperproc.georeference(ds)\n"
            "    hyperproc.to_geotiff_2d(ds, out_dir, var)"
        )
    path = _resolve(path, ds, suffix=f"_{var}", ext=FORMATS[format])

    if var not in ds and var in ds.attrs:
        # DESIS ships scene-level angles as scalars rather than rasters; make a
        # constant layer so downstream tools that expect a raster still work.
        val = float(ds.attrs[var])
        ds = ds.assign({var: (("y", "x"),
                              np.full((ds.sizes["y"], ds.sizes["x"]), val, "float32"))})
        ds[var].attrs.update(units="degrees", long_name=f"{var} (scene constant)")
    if var not in ds:
        raise ValueError(
            f"{var!r} is neither a variable nor a scene attribute. "
            f"variables: {sorted(ds.data_vars)}; "
            f"scalar attrs: {sorted(k for k, v in ds.attrs.items() if isinstance(v, float))}"
        )

    da = ds[var]
    if da.dtype == bool:
        da = da.astype("uint8")
    da = da.rio.write_crs(ds.attrs["crs"])
    affine = _transform_for(ds)
    if affine is not None:
        da = da.rio.write_transform(affine)
    if da.dtype.kind == "f":
        da = da.rio.write_nodata(np.nan, encoded=False)
    da.rio.to_raster(path, **({"compress": "deflate"} if format == "GTiff"
                              else {"driver": "ENVI", "INTERLEAVE": "BSQ"}))
    if tags:
        import rasterio
        with rasterio.open(path, "r+") as dst:
            dst.update_tags(**{k: str(v) for k, v in tags.items()})
    if overviews:
        if format == "ENVI":
            warnings.warn("ENVI has no internal pyramids; overviews were not built",
                          stacklevel=2)
        else:
            build_overviews(path, None if overviews is True else overviews,
                            resampling=overview_resampling)
    _write_stats(path)
    return path


#: The per-pixel layers a topographic or BRDF correction consumes.
GEOMETRY_LAYERS = ("slope", "aspect", "cos_i", "sza", "saa", "vza", "vaa",
                   "raa", "elev", "path_length")


def export_geometry(ds: xr.Dataset, path: str | Path,
                    layers: tuple[str, ...] | None = None,
                    overviews: bool | list[int] | None = None, overview_resampling: str = "average") -> list[Path]:
    """Write the geometry layers a topographic correction needs, one GeoTIFF each.

    Saves looping :func:`to_geotiff_2d` by hand and, more to the point, saves
    guessing which layers matter: :data:`GEOMETRY_LAYERS` is the set SCS+C, the
    C-correction and a BRDF fit actually read - slope and aspect for the facet,
    ``cos_i`` for the illumination, the four angles for the kernels, elevation
    and path length for the atmosphere.

    Whatever the dataset does not carry is skipped rather than faked, so the
    return value is the honest list of what exists for this granule.

    Args:
        ds: dataset from :func:`hyperproc.open`, orthorectified.
        path: output directory. Files are named ``<granule>_<layer>.tif``.
        layers: override the default set.

    Returns:
        The paths written, in the order attempted.
    """
    return [to_geotiff_2d(ds, path, v, overviews=overviews, overview_resampling=overview_resampling) for v in (layers or GEOMETRY_LAYERS)
            if v in ds]


def bands_to_csv(ds: xr.Dataset, path: str | Path) -> Path:
    """Write the band table: ``wavelength``, ``fwhm``, ``good_band``.

    One row per band, in the same order as the GeoTIFF from :func:`to_geotiff`,
    so row *N* is band *N* in the raster. That holds after ``wl_range``
    subsetting too, since both are written from the same dataset.

    Args:
        ds: dataset from :func:`hyperproc.open`.
        path: output ``.csv``, or a **directory**, in which case the file is
            named ``<granule>_bands.csv``.

    Returns:
        The path written.

    Note:
        ``good_band`` is ``True``/``False`` from the sensor's own flag. EMIT
        ships it on L2A only, so on an L1B granule the column is written empty
        rather than guessed.
    """
    import csv

    path = _resolve(path, ds, suffix="_bands", ext=".csv")
    wl = ds["wavelength"].values
    fwhm = ds["fwhm"].values if "fwhm" in ds.coords else [""] * len(wl)
    good = (ds["good_wavelength"].values if "good_wavelength" in ds.coords
            else [""] * len(wl))

    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["wavelength", "fwhm", "good_band"])
        for a, b, c in zip(wl, fwhm, good):
            w.writerow([f"{a:.4f}", f"{b:.4f}" if b != "" else "",
                        bool(c) if c != "" else ""])
    return path


def _write_stats(path: Path) -> None:
    """Embed per-band min/max/mean/std.

    Without these GDAL reports no statistics and QGIS falls back to a default
    stretch, which for values like latitude 37.1 or longitude -80.9 renders as
    a blank or solid-black layer.
    """
    import rasterio

    with rasterio.open(path, "r+") as dst:
        for b in range(1, dst.count + 1):
            a = dst.read(b, masked=True)
            if a.count() == 0:
                continue
            dst.update_tags(b,
                            STATISTICS_MINIMUM=float(a.min()),
                            STATISTICS_MAXIMUM=float(a.max()),
                            STATISTICS_MEAN=float(a.mean()),
                            STATISTICS_STDDEV=float(a.std()))


def _spatial_da(arr: np.ndarray, ds: xr.Dataset, projected: bool):
    """Wrap a (band, y, x) array, carrying the dataset's grid so the GeoTIFF
    gets a real transform. Without the coords rioxarray writes the identity
    matrix and the raster lands at the CRS origin instead of the scene."""
    coords = {}
    if "y" in ds.coords and "x" in ds.coords:
        coords = {"y": ds["y"].values, "x": ds["x"].values}
    da = xr.DataArray(arr, dims=("band", "y", "x"), coords=coords)
    if projected:
        da = da.rio.write_crs(ds.attrs["crs"])
        # _transform_for rebuilds the affine from the coords, so this stays
        # right for a subset and keeps any grid rotation. It also handles the
        # GDAL-vs-Affine argument order, which building Affine() positionally
        # gets wrong - that reinterprets pixel size as an origin and drops the
        # raster at the CRS origin.
        affine = _transform_for(ds)
        if affine is not None:
            da = da.rio.write_transform(affine)
    return da.rio.write_nodata(np.nan, encoded=False)


def to_latlon_geotiff(ds: xr.Dataset, path: str | Path,
                      separate: bool = False,
                      overviews: bool | list[int] | None = None, overview_resampling: str = "average") -> Path | tuple[Path, Path]:
    """Write a 2-band GeoTIFF of latitude and longitude - prismaread's ``LATLON``.

    Band 1 is latitude, band 2 longitude, both WGS-84 degrees. For a projected
    dataset the values are computed from the CRS and grid, so they are exact and
    available whether or not the granule shipped geolocation arrays. For an
    unprojected swath the granule's own ``lat``/``lon`` are written instead, and
    the file carries no CRS - the same thing prismaread does.

    Args:
        ds: dataset from :func:`hyperproc.open` or :func:`hyperproc.georeference`.
        path: output ``.tif``, or a directory to write ``<granule>_latlon.tif`` in.
        separate: write two single-band files, ``<granule>_lat.tif`` and
            ``<granule>_lon.tif``, instead of one two-band file. Two-band float
            rasters are awkward in QGIS, which tends to open them as an RGB
            composite with no blue channel and render them black; single-band
            files always open as greyscale.

    Returns:
        The path written, or both paths when ``separate=True``.
    """
    import rasterio
    import rioxarray  # noqa: F401

    path = _resolve(path, ds, suffix="_latlon")
    projected = "crs" in ds.attrs

    if projected:
        from hyperproc.grid import latlon_grid

        lat, lon = latlon_grid(ds)
        if "valid" in ds:
            m = ~np.asarray(ds["valid"].values, dtype=bool)
            lat = np.where(m, np.nan, lat)
            lon = np.where(m, np.nan, lon)
    elif "lat" in ds and "lon" in ds:
        lat, lon = ds["lat"].values, ds["lon"].values
    else:
        raise ValueError(
            "no lat/lon available. Open the granule with latlon=True, or project "
            "it with hyperproc.georeference()."
        )

    if separate:
        out = []
        for name, arr in (("lat", lat), ("lon", lon)):
            q = _resolve(path if Path(path).is_dir() or not Path(path).suffix
                         else Path(path).parent, ds, suffix=f"_{name}")
            d1 = _spatial_da(np.asarray(arr, "float32")[None], ds, projected)
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Affine.identity.*")
                d1.rio.to_raster(q, compress="deflate")
            with rasterio.open(q, "r+") as dst:
                dst.set_band_description(1, "latitude" if name == "lat" else "longitude")
                dst.update_tags(sensor=ds.attrs.get("sensor", ""), units="degrees",
                                crs_of_values="EPSG:4326")
            _write_stats(q)
            out.append(q)
        if overviews:
            for q in out:
                build_overviews(q, None if overviews is True else overviews, resampling=overview_resampling)
        return tuple(out)

    da = _spatial_da(np.stack([lat, lon]).astype("float32"), ds, projected)

    import warnings

    with warnings.catch_warnings():
        # An unprojected swath deliberately has no transform; rasterio warns
        # about that and we mean it - the lat/lon bands *are* the geolocation.
        warnings.filterwarnings("ignore", message=".*Affine.identity.*")
        da.rio.to_raster(path, compress="deflate")
        if overviews:
            build_overviews(path, None if overviews is True else overviews, resampling=overview_resampling)

    with rasterio.open(path, "r+") as dst:
        dst.set_band_description(1, "latitude")
        dst.set_band_description(2, "longitude")
        dst.update_tags(sensor=ds.attrs.get("sensor", ""),
                        level=ds.attrs.get("level", ""),
                        granule=ds.attrs.get("granule", ""),
                        units="degrees", crs_of_values="EPSG:4326")
    _write_stats(path)
    return path
