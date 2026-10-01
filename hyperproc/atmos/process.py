"""One call from an L1B granule to an atmospherically corrected GeoTIFF.

:func:`process` chains the stages the package offers and names the product by
what was done to it::

    process("EMIT_L1B_RAD_....nc", "products/")            -> <stem>_ac.tif
    process(..., stages=("ac", "brdf"))                     -> <stem>_ac_brdf.tif

The atmospheric correction runs on the sensor grid (that is where the
per-pixel geometry lives) and the result is put on a map grid afterwards:
EMIT through the granule's own geographic look-up table (GLT), exactly as
JPL's L2A ortho products are made; sensors whose L1B is already projected
(AVIRIS-3/5) need nothing; lat/lon swaths go through
:func:`hyperproc.georeference`.
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import xarray as xr

from hyperproc.atmos.correct import correct, is_complete
from hyperproc.atmos.inputs import Inputs

STAGES = ("ac", "brdf")


def _open_for_ac(path: Path) -> xr.Dataset:
    """Open a granule the way the retrieval wants it.

    EMIT is opened on its sensor grid (``ortho=False``): that is where the
    per-pixel geometry lives and where JPL runs the retrieval; the GLT puts the
    result on the map grid afterwards. Every other reader is opened with its
    defaults: the AVIRIS-5 reader also has an ``ortho`` switch, but its sensor
    grid carries no geolocation, so the correction runs on the ORT grid there.
    """
    import hyperproc as hp
    from hyperproc.registry import resolve
    try:
        sensor = str(resolve(path, None, None).sensor).upper()
    except Exception:
        sensor = ""
    if sensor == "EMIT":
        return hp.open(path, ortho=False)
    return hp.open(path)


def _ortho_emit(ds: xr.Dataset, source: Path, window: dict | None = None) -> xr.Dataset:
    """Put a sensor-grid EMIT result on the granule's ortho grid through its GLT.

    Lazy: the cube is gathered tile by tile when written. With ``window`` the
    GLT is shifted to the window's origin and the ortho grid is cropped to the
    cells the window covers.
    """
    from hyperproc.readers._common import crs_text
    from hyperproc.readers.aviris import _glt_cube
    from hyperproc.readers.emit import GLT_NODATA, _apply_glt, _stack_glt

    root = xr.open_dataset(source)
    loc = xr.open_dataset(source, group="location")
    glt = _stack_glt(loc)                      # (Y, X, 2): 1-based (crosstrack, downtrack), 0 = void
    gt = np.asarray(root.attrs["geotransform"], dtype="float64").ravel()
    row0 = col0 = 0
    if window is not None:
        y0, y1 = window["y"]; x0, x1 = window["x"]
        gx, gy = glt[..., 0], glt[..., 1]
        inside = (gx > x0) & (gx <= x1) & (gy > y0) & (gy <= y1)
        glt = np.where(inside[..., None], glt - np.array([x0, y0]), GLT_NODATA).astype(int)
        rows, cols = np.nonzero(inside)
        if rows.size == 0:
            raise ValueError("the window maps to no ortho cell")
        row0, row1, col0, col1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
        glt = glt[row0:row1, col0:col1]
    ny, nx = glt.shape[:2]
    cube = _glt_cube(ds["reflectance"].transpose("wavelength", "y", "x"), glt[..., 0], glt[..., 1]
                     ).transpose("y", "x", "wavelength")
    coords = {c: ds[c] for c in ("wavelength", "fwhm", "good_wavelength", "band_index") if c in ds.coords}
    out = xr.Dataset({"reflectance": cube}, coords=coords, attrs=dict(ds.attrs))
    out["reflectance"].attrs.update(ds["reflectance"].attrs)
    if "uncertainty" in ds:
        out["uncertainty"] = _glt_cube(ds["uncertainty"].transpose("wavelength", "y", "x"), glt[..., 0], glt[..., 1]
                                       ).transpose("y", "x", "wavelength")
        out["uncertainty"].attrs.update(ds["uncertainty"].attrs)
    for name, var in ds.data_vars.items():
        if var.ndim == 2 and var.dims == ("y", "x") and name not in ("lat", "lon"):
            out[name] = (("y", "x"), _apply_glt(np.asarray(var.values, "float32"), glt)[..., 0])
            out[name].attrs.update(var.attrs)
    out.attrs["crs"] = crs_text(root.attrs.get("spatial_ref")) or "EPSG:4326"
    out.attrs["transform"] = (gt[0] + col0 * gt[1], gt[1], gt[2], gt[3] + row0 * gt[5], gt[4], gt[5])
    out.attrs["orthorectified"] = 1
    out = out.assign_coords(x=("x", out.attrs["transform"][0] + (np.arange(nx) + 0.5) * gt[1]),
                            y=("y", out.attrs["transform"][3] + (np.arange(ny) + 0.5) * gt[5]))
    out["x"].attrs.update(units="degrees_east", standard_name="longitude")
    out["y"].attrs.update(units="degrees_north", standard_name="latitude")
    return out


def to_map_grid(ds: xr.Dataset, source: str | Path | None = None, window: dict | None = None,
                like: xr.Dataset | None = None) -> xr.Dataset:
    """A projected version of a corrected dataset, whatever grid it came on.

    * already has a CRS (AVIRIS-3/5 L1B, EnMAP L1C, Tanager): returned as is;
    * EMIT sensor grid: gathered through the granule's GLT (needs ``source``,
      the L1B file, or ``attrs["source"]`` which :func:`hyperproc.open` records);
    * anything else with ``lat``/``lon`` layers (PRISMA, DESIS, PACE):
      :func:`hyperproc.georeference`, onto the grid of ``like`` when given
      (for example ASI's PRISMA L2D, so the product compares cell for cell).
    """
    if "crs" in ds.attrs:
        if like is not None:
            warnings.warn("dataset is already projected; like= ignored", stacklevel=2)
        return ds
    src = Path(source or ds.attrs.get("source", ""))
    if str(ds.attrs.get("sensor", "")).upper() == "EMIT" and src.is_file() and like is None:
        return _ortho_emit(ds, src, window)
    if "lat" in ds and "lon" in ds:
        import hyperproc as hp
        return hp.georeference(ds, like=like)
    raise ValueError("cannot place the result on a map grid: no CRS, no GLT source and no lat/lon layers")


def process(source, out_dir, work_dir=None, engine: str = "sRTMnet", stages=("ac",), workers: int = 24,
            window: dict | None = None, overviews=True, layers=("aot550", "h2o"), uncertainty: bool = False,
            like: xr.Dataset | None = None, brdf: dict | None = None, quality: bool | dict = True,
            format: str = "GTiff", overwrite: bool = False, verbose: bool = True, **ac_kwargs) -> dict:
    """Run the requested stages on an L1B granule and write GeoTIFF products.

    Args:
        source: the L1B file (opened with the sensor-grid option where the
            reader has one) or an already opened hyperproc L1B dataset.
        out_dir: where the products go. The reflectance is
            ``<stem>_<stages joined by _>.tif`` (``..._ac.tif``), with a band
            CSV and a provenance JSON beside it, and one small GeoTIFF per
            entry of ``layers`` (``..._ac_aot550.tif``, ``..._ac_h2o.tif``).
        work_dir: ISOFIT working directory; default ``out_dir/isofit_work/<stem>``.
            Reused when it already holds a finished run (see :func:`correct`).
        engine, workers, **ac_kwargs: passed to :func:`hyperproc.atmos.correct`
            (``atmosphere``, ``surface``, ``segmentation_size``, ``line``, ...).
        stages: ``("ac",)`` for atmospheric correction only. ``("ac", "brdf")``
            also normalises the Sun and view geometry with the MODIS c-factor
            (:func:`hyperproc.correct.nbar`) before the product is projected,
            and names the product ``<stem>_ac_brdf.tif``. Airborne flightlines
            are not corrected this way: FlexBRDF is fitted on a flightline
            group in :mod:`hyperproc.correct` instead.
        brdf: options for the BRDF stage, passed to
            :func:`hyperproc.correct.nbar` (``sza_ref``, ``spectral``,
            ``params``, ``cache_dir``, ``project``, ...).
        format: ``"GTiff"`` (default) or ``"ENVI"``. ENVI writes a flat binary
            with a ``.hdr`` that states the wavelengths, widths and bad-band
            list as numbers rather than as band labels, at the cost of no
            compression: a full EMIT product is about 5.1 GB against 2.2 GB.
            Overviews are not built for ENVI.
        quality: write ``<stem>_quality.tif``, the consolidated flag layer
            (:mod:`hyperproc.quality`), beside the product. A dict is passed
            through to :func:`hyperproc.quality.build`; False skips it.
        window: sensor-grid subset ``{"y": (y0, y1), "x": (x0, x1)}`` for
            trial runs; the product then covers only that footprint.
        overviews: internal pyramids on every GeoTIFF written (default True).
        layers: 2-D retrieval layers to write as separate GeoTIFFs.
        uncertainty: also write the posterior uncertainty cube (``..._uncert.tif``).
        like: for swath sensors, a projected dataset whose grid the product
            should reproduce (see :func:`to_map_grid`).
        overwrite: redo the ISOFIT retrieval even if the work dir holds one.

    Returns:
        dict with ``reflectance`` (path), ``layers`` (name -> path),
        ``provenance`` (path), ``work_dir``, ``seconds`` and ``dataset``
        (the projected, lazy dataset that was written).
    """
    import hyperproc as hp
    from hyperproc.io import FORMATS, bands_to_csv, to_geotiff_2d, to_raster

    if format not in FORMATS:
        raise ValueError(f"format must be one of {sorted(FORMATS)}; got {format!r}")
    ext = FORMATS[format]

    stages = tuple(stages)
    if not stages or stages[0] != "ac" or any(s not in STAGES for s in stages):
        raise ValueError(f"stages must start with 'ac' and use only {STAGES}; got {stages}")
    t0 = time.time()
    if isinstance(source, (str, Path)):
        src_path = Path(source).expanduser().resolve()
        ds = _open_for_ac(src_path)
    else:
        ds = source
        src_path = Path(ds.attrs.get("source", "")) if ds.attrs.get("source") else None
    stem = str(ds.attrs.get("stem") or ds.attrs.get("granule") or "scene")
    out_dir = Path(out_dir).expanduser(); out_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(work_dir) if work_dir else out_dir / "isofit_work" / stem
    if verbose:
        print(f"process: {stem}  stages {stages}  engine {engine}  work {work_dir}")

    rfl = correct(ds, work_dir, engine=engine, workers=workers, window=window, overwrite=overwrite,
                  verbose=verbose, **ac_kwargs)
    if src_path is not None:
        rfl.attrs.setdefault("source", str(src_path))
    if "brdf" in stages:
        from hyperproc.correct.cfactor import nbar
        from hyperproc.correct.pipeline import is_airborne
        if is_airborne(rfl):
            raise ValueError("the 'brdf' stage here is the MODIS c-factor normalisation, which assumes a "
                             "satellite's narrow view cone; an airborne flightline has the angular spread to "
                             "fit its own kernels, so use hyperproc.correct.fit_brdf/apply on the group")
        rfl = nbar(rfl, keep_c=False, verbose=verbose, **(brdf or {}))
    mapped = to_map_grid(rfl, src_path, window, like=like)
    name = rfl.attrs["stem"]                          # <stem>_ac
    if window is not None:
        name += f"_win{window['y'][0]}-{window['y'][1]}_{window['x'][0]}-{window['x'][1]}"
    if verbose:
        print(f"writing {name}.tif  ({dict(mapped.sizes)}) ...", flush=True)
    paths = {"reflectance": to_raster(mapped, out_dir / f"{name}{ext}", format=format,
                                      **({"overviews": overviews} if format == "GTiff" else {})),
             "layers": {}}
    bands_to_csv(mapped, out_dir / f"{name}_bands.csv")
    for layer in layers or ():
        if layer in mapped:
            paths["layers"][layer] = to_geotiff_2d(
                mapped, out_dir / f"{name}_{layer}{ext}", var=layer, format=format,
                overviews=overviews if format == "GTiff" else None)
        else:
            warnings.warn(f"layer {layer!r} not in the result; skipped", stacklevel=2)
    if quality is not False:
        from hyperproc.quality import FLAGS, FLAG_DESCRIPTIONS, build as build_quality, summary as quality_summary
        opts = dict(quality) if isinstance(quality, dict) else {}
        opts.setdefault("derive", ("fill",) + (("terrain_shadow",) if "cos_i" in mapped else ()))
        q = build_quality(mapped, **opts)
        mapped["quality"] = q
        paths["quality"] = to_geotiff_2d(
            mapped, out_dir / f"{name}_quality{ext}", var="quality", format=format,
            overviews=overviews if format == "GTiff" else None,
            overview_resampling="nearest",          # averaging bit flags would be meaningless
            tags={"flag_bits": q.attrs["flag_bits"], "flag_masks": q.attrs["flag_masks"],
                  "flag_meanings": q.attrs["flag_meanings"], "sources": q.attrs["sources"]})
        quality_shares = {k: round(v, 5) for k, v in quality_summary(q).items() if v > 0}
        if verbose:
            print("quality: " + ", ".join(f"{k} {v * 100:.1f}%" for k, v in quality_shares.items()))
    if uncertainty and "uncertainty" in mapped:
        paths["uncertainty"] = to_raster(
            mapped, out_dir / f"{name}_uncert{ext}", format=format, var="uncertainty",
            **({"overviews": overviews} if format == "GTiff" else {}))
    inputs = Inputs.load(work_dir)
    rec = json.loads((Path(work_dir) / "hyperproc_ac.json").read_text()) if (Path(work_dir) / "hyperproc_ac.json").is_file() else {}
    prov = {"product": str(paths["reflectance"]), "stages": list(stages), "stem": stem, "source": str(src_path or ""),
            "sensor": ds.attrs.get("sensor"), "granule": ds.attrs.get("granule"), "datetime": ds.attrs.get("datetime"),
            "window": window, "grid": {"crs": mapped.attrs.get("crs"), "transform": list(mapped.attrs.get("transform", ())),
                                       "shape": [mapped.sizes["y"], mapped.sizes["x"], mapped.sizes["wavelength"]]},
            "atmospheric_correction": {k[3:]: v for k, v in rfl.attrs.items() if k.startswith("ac_")},
            "isofit": {"command": rec.get("command"), "version": rec.get("isofit_version"), "seconds": rec.get("seconds"),
                       "work_dir": str(work_dir), "fid": inputs.fid, "sensor_code": inputs.code},
            "layers": {k: str(v) for k, v in paths["layers"].items()},
            "format": format, "overviews": bool(overviews) and format == "GTiff",
            "quality": ({"file": str(paths["quality"]), "bits": dict(FLAGS),
                         "descriptions": dict(FLAG_DESCRIPTIONS), "shares": quality_shares}
                        if quality is not False else None),
            "hyperproc": hp.__version__, "written": time.strftime("%Y-%m-%dT%H:%M:%S"), "seconds": round(time.time() - t0, 1)}
    paths["provenance"] = out_dir / f"{name}_provenance.json"
    paths["provenance"].write_text(json.dumps(prov, indent=1, default=str))
    paths.update(work_dir=work_dir, seconds=prov["seconds"], dataset=mapped)
    if verbose:
        print(f"done in {prov['seconds'] / 60:.1f} min -> {paths['reflectance']}")
    return paths
