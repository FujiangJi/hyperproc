#!/usr/bin/env python
"""hyperproc end to end on one EMIT granule, in one self-contained file.

This is the same pipeline as `emit_pipeline.py`, written out in full instead of
configuring the shared engine in `pipeline.py`. Both work and both produce the
same products.

    emit_pipeline.py              40 lines, uses pipeline.py
    emit_pipeline_standalone.py  881 lines, depends on nothing but hyperproc

The standalone is kept for reading and for lifting: everything a run does is
visible in one place, in order, which is easier to follow than a config plus a
generic engine, and easier to copy into a project that wants one sensor and
not the rest. The cost is that a fix made here reaches no other sensor - all
four bugs in this folder's history were found once and fixed once in the
engine, and would have had to be found six times without it.


Starts from nothing on disk: finds a granule, downloads the matched L1B/L2A
pair, reads both, exports both in two formats, then runs the two correction
routes and compares them.

    L1B radiance  --atmospheric-->  reflectance  --BRDF-->  normalised
    L2A reflectance               (JPL's own AC)  --BRDF-->  normalised

The point of running both is the comparison at the end: our retrieval against
JPL's over the same ground, and each BRDF step against its own input.

Layout, all relative to py_tests/:

    1_data/EMIT/                  the downloaded granule pair
    2_outputs/EMIT/01_read/       the read-and-export demonstration
    2_outputs/EMIT/02_ac/         L1B -> reflectance
    2_outputs/EMIT/03_ac_brdf/    L1B -> reflectance -> BRDF
    2_outputs/EMIT/04_l2a_brdf/   L2A -> BRDF
    2_outputs/EMIT/figures/       every figure, as PNG
    2_outputs/EMIT/summary.json   what ran, how long it took, what it measured

Usage:

    python emit_pipeline.py                      # the whole thing
    python emit_pipeline.py --skip-download      # reuse what is in 1_data
    python emit_pipeline.py --stage read         # stop after reading and exporting
    python emit_pipeline.py --window 1080 1200 840 960 --workers 20

Needs, in this order:
  * an Earthdata login for the download   - pip install 'hyperproc[search]'
  * ISOFIT and its assets for the AC      - pip install 'hyperproc[atmos]'
                                            then hyperproc-atmos-setup
  * Earth Engine credentials for the BRDF - pip install 'hyperproc[brdf]'
                                            then earthengine authenticate
Each stage checks for its own and says what is missing rather than failing
halfway through.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------- #
# where things live                                                            #
# --------------------------------------------------------------------------- #

HERE = Path(__file__).resolve().parent          # py_tests/0_src_code
PY_TESTS = HERE.parent                          # py_tests
SENSOR = "EMIT"

DATA = PY_TESTS / "1_data" / SENSOR
OUT = PY_TESTS / "2_outputs" / SENSOR
FIGS = OUT / "figures"

# ISOFIT caches surface priors and elevation tiles under the output tree rather
# than in your home directory. The working directory is named after the window
# by work_dir_for(): process() deliberately reuses a retrieval it finds there,
# which is what makes the AC+BRDF run take seconds instead of minutes - and
# which silently reuses the *wrong* retrieval if two windows share one folder.
MODIS_DIR = OUT / "03_ac_brdf" / "mcd43"
os.environ.setdefault("HYPERPROC_CACHE_DIR", str(OUT / "cache"))


# --------------------------------------------------------------------------- #
# the control panel                                                            #
# --------------------------------------------------------------------------- #

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)

    g = p.add_argument_group("what to find")
    g.add_argument("--bbox", nargs=4, type=float, metavar=("W", "S", "E", "N"),
                   default=[-121.0, 34.0, -119.8, 35.1],
                   help="search box in degrees (default: the California coast "
                        "the EMIT tutorial uses)")
    g.add_argument("--date", nargs=2, metavar=("FROM", "TO"),
                   default=["2023-01-01", "2024-12-31"],
                   help="YYYY-MM-DD YYYY-MM-DD")
    g.add_argument("--max-cloud", type=float, default=20.0,
                   help="reject granules cloudier than this percent (default 20)")

    g = p.add_argument_group("what to process")
    g.add_argument("--window", nargs=4, type=int, metavar=("Y0", "Y1", "X0", "X1"),
                   default=[1080, 1200, 840, 960],
                   help="rows and columns on the DETECTOR grid (default "
                        "1080 1200 840 960, a 120x120 subset over vegetation: "
                        "NDVI +0.72, 97 %% vegetated on the granule this script "
                        "picks by default. The tutorial's 600 720 600 720 lands "
                        "on open water in that scene, where the BRDF step has "
                        "no land signal to work on. Step 2 reports what your "
                        "window actually contains. Pass 0 0 0 0 for the whole "
                        "granule, about an hour rather than a few minutes")
    g.add_argument("--workers", type=int, default=20,
                   help="cores for the ISOFIT retrieval (default 20)")
    g.add_argument("--sza-ref", default="45.0",
                   help="sun zenith to normalise to, or 'observed' to keep each "
                        "pixel's own (default 45.0)")
    g.add_argument("--vza-ref", type=float, default=0.0,
                   help="view zenith to normalise to (default 0.0, nadir)")
    g.add_argument("--diag-nm", type=float, default=865.0,
                   help="wavelength used for every map and comparison (default 865)")

    g = p.add_argument_group("how far to go")
    g.add_argument("--stage", choices=["download", "read", "ac", "brdf", "all"],
                   default="all", help="stop after this stage (default all)")
    g.add_argument("--skip-download", action="store_true",
                   help="use whatever EMIT pair is already in 1_data/EMIT")
    g.add_argument("--format", choices=["GTiff", "ENVI"], default="GTiff",
                   help="format for the correction products; the read step "
                        "writes both whatever this says (default GTiff)")
    g.add_argument("--no-figures", action="store_true")

    args = p.parse_args(argv)
    if args.window == [0, 0, 0, 0]:
        args.window = None
    else:
        y0, y1, x0, x1 = args.window
        args.window = {"y": (y0, y1), "x": (x0, x1)}
    args.sza_ref = "observed" if args.sza_ref == "observed" else float(args.sza_ref)
    return args


# --------------------------------------------------------------------------- #
# small helpers                                                                #
# --------------------------------------------------------------------------- #

def work_dir_for(window):
    """ISOFIT's working directory, one per window.

    Sharing it between windows means the second run finds a finished retrieval
    and reuses it: same numbers, same reported runtime, painted onto different
    ground. That is not a hypothetical - it happened on the first run of this
    script, and the only visible symptom was a flat, too-dark first panel.
    """
    if window is None:
        return OUT / "02_ac" / "isofit_full"
    y0, y1 = window["y"]
    x0, x1 = window["x"]
    return OUT / "02_ac" / f"isofit_win{y0}-{y1}_{x0}-{x1}"


STEP = 0


def step(title):
    """Print a banner, so a long run is readable in a terminal or a log file."""
    global STEP
    STEP += 1
    print(f"\n{'=' * 78}\n{STEP}. {title}\n{'=' * 78}", flush=True)


def say(*parts):
    print("   ", *parts, flush=True)


def raster_grid(path):
    """Pixel-centre coordinates (x, y) of a raster on disk."""
    import numpy as np
    import rasterio
    with rasterio.open(path) as src:
        tr = src.transform
        return (tr.c + (np.arange(src.width) + 0.5) * tr.a,
                tr.f + (np.arange(src.height) + 0.5) * tr.e)


def same_ground(ds, x, y):
    """The part of ``ds`` covering those coordinates, to within one pixel.

    Products written from a window are a different grid from the granule they
    came from, so lining them up by row and column number would compare two
    different pieces of ground. Line them up by coordinate instead.
    """
    tol = abs(float(ds.x[1] - ds.x[0]))
    return ds.sel(x=x, y=y, method="nearest", tolerance=tol)


def read_product(path, var="reflectance", geometry_from=None):
    """Read a product this package wrote back into a dataset.

    ``hyperproc.open`` refuses its own products on purpose - they carry no
    geometry, so a correction that needs angles would silently get none. Taking
    the angles from the granule, by coordinate, is what makes the reloaded cube
    usable again.
    """
    import numpy as np
    import rasterio
    import xarray as xr

    with rasterio.open(path) as src:
        envi = src.tags(ns="ENVI")
        if "wavelength" in envi:                   # ENVI states them as numbers
            wl = np.array([float(v) for v in envi["wavelength"].strip("{}").split(",")])
        else:                                      # GeoTIFF: parse the band labels
            wl = np.array([float(d.split()[0]) for d in src.descriptions])
        cube = src.read().astype("float32")
        tr, crs, ny, nx = src.transform, str(src.crs), src.height, src.width

    ds = xr.Dataset(
        {var: (("y", "x", "wavelength"), np.moveaxis(cube, 0, -1))},
        coords={"wavelength": wl,
                "x": tr.c + (np.arange(nx) + 0.5) * tr.a,
                "y": tr.f + (np.arange(ny) + 0.5) * tr.e},
        attrs={"crs": crs, "transform": tuple(tr.to_gdal()), "sensor": SENSOR,
               "stem": Path(path).stem, "units": "1"})
    if geometry_from is not None:
        g = same_ground(geometry_from, ds.x.values, ds.y.values)
        for layer in ("sza", "saa", "vza", "vaa", "raa"):
            if layer in g:
                ds[layer] = (("y", "x"), g[layer].values)
    return ds


def describe_window(ds, var="reflectance"):
    """What is in the window: bright or dark, vegetated or not, water or land.

    Worth a few seconds before anything expensive. The BRDF route borrows its
    angular shape from MODIS land kernels, so a window of open water produces
    numbers that look like results and mean very little - and a dark target
    makes the atmospheric comparison mostly a comparison of path radiance.
    """
    import numpy as np
    if var not in ds:
        return {}
    red = ds[var].isel(wavelength=band_at(ds, 660)).values
    nir = ds[var].isel(wavelength=band_at(ds, 865)).values
    ok = np.isfinite(red) & np.isfinite(nir)
    if ok.sum() < 20:
        say("the window is almost entirely fill; move it")
        return {"valid_fraction": float(ok.mean())}
    ndvi = (nir[ok] - red[ok]) / (nir[ok] + red[ok] + 1e-9)
    out = {"valid_fraction": float(ok.mean()),
           "median_ndvi": float(np.median(ndvi)),
           "median_nir": float(np.median(nir[ok])),
           "vegetated_fraction": float((ndvi > 0.3).mean())}
    say(f"window content: NDVI {out['median_ndvi']:+.3f}, "
        f"865 nm {out['median_nir']:.3f}, "
        f"{out['vegetated_fraction'] * 100:.0f} % vegetated, "
        f"{out['valid_fraction'] * 100:.0f} % valid")
    if out["median_nir"] < 0.06 and out["median_ndvi"] < 0.15:
        out["warning"] = "looks like open water"
        say("  ^ that reads as open water. The BRDF step borrows MODIS *land*")
        say("    kernels, so its output here will look like a result and mean")
        say("    little. Move the window with --window Y0 Y1 X0 X1.")
    return out


def band_at(ds, nm):
    """Index of the band nearest a wavelength."""
    import numpy as np
    return int(np.argmin(np.abs(ds.wavelength.values - nm)))


def mean_spectrum(cube, max_pixels=20000):
    """Mean over pixels, ignoring NaN, on a subsample if the cube is large."""
    import numpy as np
    a = cube.values if hasattr(cube, "values") else cube
    flat = a.reshape(-1, a.shape[-1])
    if flat.shape[0] > max_pixels:
        idx = np.linspace(0, flat.shape[0] - 1, max_pixels).astype(int)
        flat = flat[idx]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.nanmean(flat, axis=0)


def limits(*images, lo=2, hi=98):
    """Colour limits from the data, shared across every image given.

    Hard-coding vmin=0, vmax=0.5 is what made the first run of this script
    render a water window as solid black: the reflectance there is 0.02-0.04,
    which is the bottom 6 % of that scale. Percentiles adapt; passing several
    images together keeps a before/after pair on one scale, so a difference in
    the picture is a difference in the data and not in the stretch.
    """
    import numpy as np
    vals = np.concatenate([np.asarray(i).ravel() for i in images])
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return 0.0, 1.0
    a, b = np.percentile(vals, [lo, hi])
    if not np.isfinite([a, b]).all() or b <= a:
        a, b = float(np.nanmin(vals)), float(np.nanmax(vals)) or 1.0
    return float(a), float(b)


def savefig(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / name
    fig.savefig(path, dpi=140, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    say(f"figure -> {path.relative_to(PY_TESTS)}")
    return path


# --------------------------------------------------------------------------- #
# 1. find and download a matched L1B / L2A pair                                #
# --------------------------------------------------------------------------- #

def find_and_download(args, hp):
    """One granule, both levels, same scene.

    The comparison at the end only means anything if the L1B we correct and the
    L2A we compare it against are the same acquisition. EMIT names make that
    checkable: the two differ only in the product code, so the L2A is found by
    name rather than by searching the same box again and hoping.
    """
    step("find a granule and download it")
    DATA.mkdir(parents=True, exist_ok=True)

    have_l1b = sorted(DATA.glob("EMIT_L1B_RAD_*.nc"))
    have_l2a = sorted(DATA.glob("EMIT_L2A_RFL_*.nc"))
    if args.skip_download:
        if not (have_l1b and have_l2a):
            sys.exit(f"--skip-download, but {DATA} has no EMIT pair")
        say(f"using what is already there: {have_l1b[0].name}")
        return have_l1b[0], have_l2a[0]

    if not hp.archive.can_download("EMIT", "L1B"):
        who, need = hp.archive.BACKENDS["cmr"]
        sys.exit(f"no credentials for {who}; it needs {need}\n"
                 f"    register, then put them in ~/.netrc or EARTHDATA_USERNAME/"
                 f"EARTHDATA_PASSWORD, or rerun with --skip-download")

    hits = hp.search("EMIT", "L1B", bbox=tuple(args.bbox), date=tuple(args.date),
                     cloud=(0, args.max_cloud), count=20)
    if not len(hits):
        sys.exit("nothing matched; widen --bbox, --date or --max-cloud")

    # the clearest, then the smallest among equals: a cloudy window makes every
    # comparison below a comparison of clouds
    pick = min(hits, key=lambda g: (g.cloud if g.cloud is not None else 100, g.size_mb))
    say(f"chosen {pick.name}")
    say(f"  {pick.time:%Y-%m-%d %H:%M}, {pick.cloud:.0f}% cloud, {pick.size_mb:,.0f} MB")

    l2a_name = pick.name.replace("L1B_RAD", "L2A_RFL")
    mate = hp.search("EMIT", "L2A", granule_name=l2a_name, count=1, verbose=False)
    if not len(mate):
        sys.exit(f"the matching L2A ({l2a_name}) is not in CMR; try another granule")
    say(f"its L2A  {mate[0].name}  ({mate[0].size_mb:,.0f} MB)")

    total = (pick.size_mb + mate[0].size_mb) / 1024
    say(f"downloading {total:.1f} GB into {DATA.relative_to(PY_TESTS)} ...")
    t0 = time.time()
    hp.download([pick, mate[0]], DATA, workers=4)
    say(f"{(time.time() - t0) / 60:.1f} min")

    l1b = sorted(DATA.glob("EMIT_L1B_RAD_*.nc"))[0]
    l2a = sorted(DATA.glob("EMIT_L2A_RFL_*.nc"))[0]
    for f in sorted(DATA.glob("EMIT_*")):
        say(f"  {f.name}  {f.stat().st_size / 1e9:.2f} GB")
    return l1b, l2a


# --------------------------------------------------------------------------- #
# 2. read both levels, and export in both formats                              #
# --------------------------------------------------------------------------- #

def read_and_export(args, hp, l1b_path, l2a_path):
    step("read both levels, export both formats")
    import numpy as np

    say("sniff:", hp.sniff(l1b_path), "|", hp.sniff(l2a_path))
    l1b = hp.open(l1b_path)                       # radiance, orthorectified
    l2a = hp.open(l2a_path)                       # JPL's surface reflectance
    l1b_sensor = hp.open(l1b_path, ortho=False)   # the detector grid the retrieval runs on

    # WINDOW counts rows and columns on the DETECTOR grid. The ortho grid is a
    # different grid, so the same numbers there would land somewhere else - on
    # this granule, out at sea. Take the ground the detector window covers.
    if args.window is None:
        l2a_sub, l1b_sub = l2a, l1b
    else:
        w = l1b_sensor.isel(y=slice(*args.window["y"]), x=slice(*args.window["x"]))
        west, east = float(w.lon.min()), float(w.lon.max())
        south, north = float(w.lat.min()), float(w.lat.max())
        l2a_sub = l2a.sel(x=slice(west, east), y=slice(north, south))   # y runs N to S
        l1b_sub = l1b.sel(x=slice(west, east), y=slice(north, south))
        say(f"window {args.window} on the detector grid covers "
            f"{west:.3f}..{east:.3f} E, {south:.3f}..{north:.3f} N")

    for name, ds in (("L1B ortho", l1b), ("L1B detector", l1b_sensor),
                     ("L2A", l2a), ("L2A window", l2a_sub)):
        say(f"{name:14s} {dict(ds.sizes)}  var={hp.main_var(ds)}  "
            f"units={ds.attrs.get('units')}")

    summary_window = describe_window(l2a_sub)

    say("geometry layers on the L1B:",
        ", ".join(v for v in ("sza", "saa", "vza", "vaa", "raa", "elev") if v in l1b))

    # Export a small piece in both formats. Both levels, so the pair can be
    # opened in ENVI, QGIS or anything else without rerunning this script.
    out = OUT / "01_read"
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for label, ds in (("l1b_radiance", l1b_sub), ("l2a_reflectance", l2a_sub)):
        t0 = time.time()
        tif = hp.to_geotiff(ds, out / f"{label}.tif", overviews=True)
        img = hp.to_envi(ds, out / f"{label}.img", interleave="bil")
        hp.bands_to_csv(ds, out / f"{label}_bands.csv")
        written[label] = {"GTiff": str(tif), "ENVI": str(img)}
        say(f"{label:16s} GeoTIFF {tif.stat().st_size / 1e6:7.1f} MB   "
            f"ENVI {img.stat().st_size / 1e6:7.1f} MB   ({time.time() - t0:.1f} s)")

    # what the ENVI header carries that a GeoTIFF cannot
    hdr = (out / "l2a_reflectance.hdr").read_text().splitlines()
    for line in hdr:
        if line.split("=")[0].strip() in ("wavelength units", "interleave", "sensor"):
            say("  hdr:", line.strip())
        for key in ("wavelength =", "fwhm =", "bbl ="):
            if line.startswith(key):
                say(f"  hdr: {key:14s} {line.split('=', 1)[1].strip()[:54]} ...")

    return l1b, l2a, l1b_sub, l2a_sub, written, summary_window


# --------------------------------------------------------------------------- #
# 3. L1B -> atmospheric correction                                             #
# --------------------------------------------------------------------------- #

def run_ac(args, hp, l1b_path):
    step("L1B radiance -> surface reflectance (ISOFIT)")
    from hyperproc.atmos import check, process

    report = check(engines=("sRTMnet",))
    if not report["ok"]:
        say("ISOFIT assets are not in place; run hyperproc-atmos-setup --check")
        return None
    say("ISOFIT assets ready")

    t0 = time.time()
    work_dir = work_dir_for(args.window)
    say(f"ISOFIT work dir {work_dir.name}"
        f"{'  (reusing the retrieval found there)' if work_dir.exists() else ''}")
    ac = process(l1b_path, OUT / "02_ac", work_dir=work_dir, stages=("ac",),
                 workers=args.workers, window=args.window, format=args.format,
                 layers=("aot550", "h2o"), overviews=True, verbose=True)
    say(f"{(time.time() - t0) / 60:.1f} min -> {Path(ac['reflectance']).name}")
    say("layers :", {k: Path(v).name for k, v in ac["layers"].items()})

    prov = json.loads(Path(ac["provenance"]).read_text())
    say(f"grid   {prov['grid']['shape']}  {prov['grid']['crs']}")
    say(f"isofit v{prov['isofit']['version']}, {prov['isofit']['seconds']} s")
    say("quality " + ", ".join(f"{k} {v * 100:.1f}%"
                               for k, v in prov["quality"]["shares"].items()))
    return ac


# --------------------------------------------------------------------------- #
# 4. BRDF, on both routes                                                      #
# --------------------------------------------------------------------------- #

def fetch_modis(hp, l2a):
    """MODIS MCD43A1 kernel weights for this footprint and date.

    One overpass cannot measure its own angular response, so the c-factor
    method borrows the shape from MODIS. This is the step that needs Earth
    Engine credentials.
    """
    from hyperproc.correct import mcd43
    try:
        params = mcd43.fetch(ds=l2a, out_dir=MODIS_DIR, verbose=True)
    except Exception as exc:
        say(f"MODIS parameters unavailable: {type(exc).__name__}: {exc}")
        say("  the BRDF route needs Earth Engine: pip install 'hyperproc[brdf]'")
        say("  then: earthengine authenticate")
        return None
    say(f"MODIS {params.shape} at {abs(params.transform[0]) * 111320:.0f} m, "
        f"date {params.date}, {params.coverage() * 100:.0f} % of cells retrieved")
    return params


def run_ac_brdf(args, hp, l1b_path, params):
    step("L1B -> reflectance -> BRDF, in one call")
    from hyperproc.atmos import process
    t0 = time.time()
    acb = process(l1b_path, OUT / "03_ac_brdf", work_dir=work_dir_for(args.window),
                  stages=("ac", "brdf"), workers=args.workers, window=args.window,
                  format=args.format, overviews=True,
                  brdf=dict(params=params, sza_ref=args.sza_ref,
                            vza_ref=args.vza_ref, spectral="nearest", fill="none"),
                  verbose=True)
    say(f"{(time.time() - t0) / 60:.1f} min -> {Path(acb['reflectance']).name}")
    say("the retrieval was reused from the work directory; only BRDF and the export ran")
    return acb


def run_l2a_brdf(args, hp, l2a_sub, params):
    step("L2A reflectance -> BRDF")
    t0 = time.time()
    brdf = hp.correct.nbar(l2a_sub, params=params, sza_ref=args.sza_ref,
                           vza_ref=args.vza_ref, spectral="nearest", fill="none",
                           cache_dir=MODIS_DIR)
    say(f"built in {time.time() - t0:.1f} s (lazy); stem {brdf.attrs['stem']}")
    for k, v in brdf.attrs.items():
        if k.startswith("brdf_"):
            say(f"  {k:24s} {v}")

    ext = hp.FORMATS[args.format]
    out = OUT / "04_l2a_brdf"
    out.mkdir(parents=True, exist_ok=True)
    slim = brdf.drop_vars([v for v in ("c_factor", "modis_band") if v in brdf.variables])
    t0 = time.time()
    kw = {"overviews": True} if args.format == "GTiff" else {}
    p = hp.to_raster(slim, out / f"{brdf.attrs['stem']}{ext}", format=args.format, **kw)
    hp.bands_to_csv(slim, out / f"{brdf.attrs['stem']}_bands.csv")
    say(f"wrote {p.name} ({p.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.1f} s")
    return brdf, p


def judge_brdf(hp, before, after, params, nm):
    """Did the correction do what a correction should?

    Two measurable questions, both of which can answer "cannot tell on this
    scene" - a 120 x 120 window often spans too little view angle to see any
    trend, and that is a fact about the window, not a failure.
    """
    from hyperproc.correct import cfactor
    out = {}
    try:
        prof = cfactor.view_profile(before, after, wavelength=nm, step=0.25, stride=3)
        out["view_profile"] = {k: float(v) for k, v in prof.items()
                               if isinstance(v, (int, float))}
        say(f"view-angle slope at {nm:.0f} nm: {prof['slope_before'] * 1000:+.3f} -> "
            f"{prof['slope_after'] * 1000:+.3f} e-3 per degree "
            f"over {prof['vza_span']:.2f} deg")
    except ValueError as exc:
        say("view profile not available:", exc)
    try:
        agree = cfactor.model_agreement(before, params.masked(), wavelength=nm, stride=2)
        out["model_agreement"] = {"r": float(agree["r"]),
                                  "r_flipped": float(agree["r_flipped"]),
                                  "verdict": agree["verdict"]}
        say(f"model agreement r={agree['r']:+.3f} "
            f"(flipped {agree['r_flipped']:+.3f}) -> {agree['verdict']}")
    except ValueError as exc:
        say("model agreement not testable:", exc)
    return out


# --------------------------------------------------------------------------- #
# 5. the quality layer                                                         #
# --------------------------------------------------------------------------- #

def quality(hp, l2a_sub):
    step("quality flags")
    import numpy as np
    q = hp.quality_flags(l2a_sub, derive=("fill", "terrain_shadow"))
    meanings = q.attrs.get("flag_meanings", "").split()
    # CF states flag_masks as a space-separated string here, though the
    # convention also allows an array; accept either rather than assume
    masks = q.attrs.get("flag_masks", "")
    masks = masks.split() if isinstance(masks, str) else list(masks)
    shares = {}
    for name, bit in zip(meanings, masks):
        shares[name] = float(((q.values & int(bit)) > 0).mean())
    for name, frac in sorted(shares.items(), key=lambda kv: -kv[1]):
        if frac > 0:
            say(f"{name:18s} {frac * 100:5.1f} %")
    clear = hp.quality_apply(l2a_sub, q,
                             drop=("fill", "cloud", "cloud_shadow", "cirrus"))
    kept = float(np.isfinite(clear[hp.main_var(clear)].isel(wavelength=0)).mean())
    say(f"{kept * 100:.1f} % of pixels survive the default mask")
    return q, shares


# --------------------------------------------------------------------------- #
# 6. figures                                                                   #
# --------------------------------------------------------------------------- #

def figure_inputs(hp, l1b_sub, l2a_sub, nm):
    """What went in: radiance and JPL's reflectance, same ground, same band."""
    import matplotlib.pyplot as plt
    import numpy as np

    rad = l1b_sub[hp.main_var(l1b_sub)].isel(wavelength=band_at(l1b_sub, nm)).values
    ref = l2a_sub.reflectance.isel(wavelength=band_at(l2a_sub, nm)).values
    rlo, rhi = limits(rad)
    flo, fhi = limits(ref)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    for a, img, title, kw in (
            (ax[0], rad, f"L1B radiance @ {nm:.0f} nm",
             dict(cmap="magma", vmin=rlo, vmax=rhi)),
            (ax[1], ref, f"L2A reflectance @ {nm:.0f} nm",
             dict(cmap="gray", vmin=flo, vmax=fhi))):
        im = a.imshow(img, **kw)
        a.set_title(title)
        a.set_xticks([]); a.set_yticks([])
        plt.colorbar(im, ax=a, fraction=0.046)
    fig.suptitle(f"{SENSOR}: the two levels this script starts from", y=1.02)
    return savefig(fig, "01_inputs.png")


def figure_geometry(l1b_sub):
    """The angles the BRDF step uses. Without these, nothing below is possible."""
    import matplotlib.pyplot as plt
    layers = [v for v in ("sza", "vza", "raa", "saa", "vaa", "elev") if v in l1b_sub]
    if not layers:
        return None
    n = len(layers)
    fig, ax = plt.subplots(1, n, figsize=(3.4 * n, 3.6))
    ax = [ax] if n == 1 else list(ax)
    for a, name in zip(ax, layers):
        im = a.imshow(l1b_sub[name].values, cmap="viridis")
        unit = l1b_sub[name].attrs.get("units", "")
        a.set_title(f"{name}  ({unit})")
        a.set_xticks([]); a.set_yticks([])
        plt.colorbar(im, ax=a, fraction=0.046)
    fig.suptitle("observation geometry, from the L1B", y=1.04)
    return savefig(fig, "02_geometry.png")


def figure_ac_vs_jpl(ac, l2a, nm):
    """Our retrieval against JPL's, as maps and as a scatter.

    These are two independent atmospheric corrections of the same radiance, so
    the difference is the thing to look at, not the agreement.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    import rasterio

    with rasterio.open(ac["reflectance"]) as src:
        wl = np.array([float(d.split()[0]) for d in src.descriptions])
        ours = src.read(int(np.argmin(np.abs(wl - nm))) + 1)
    xs, ys = raster_grid(ac["reflectance"])
    theirs = same_ground(
        l2a.reflectance.isel(wavelength=band_at(l2a, nm)), xs, ys).values

    ok = np.isfinite(ours) & np.isfinite(theirs) & (ours > 0) & (theirs > 0)
    stats = {}
    if ok.sum() > 10:
        d = ours[ok] - theirs[ok]
        stats = {"n": int(ok.sum()), "median_difference": float(np.median(d)),
                 "rmse": float(np.sqrt(np.mean(d ** 2))),
                 "r": float(np.corrcoef(ours[ok], theirs[ok])[0, 1])}
        say(f"at {nm:.0f} nm over {stats['n']:,} pixels: "
            f"median {stats['median_difference']:+.4f}, "
            f"RMSE {stats['rmse']:.4f}, r {stats['r']:.4f}")

    lim = float(np.nanpercentile(np.abs(ours - theirs), 98)) or 0.02
    lo, hi = limits(ours, theirs)          # one scale, or the two are not comparable
    fig, ax = plt.subplots(1, 4, figsize=(19, 4.0))
    for a, img, title, kw in (
            (ax[0], ours, "hyperproc + ISOFIT", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[1], theirs, "JPL L2A", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[2], ours - theirs, "ours - JPL",
             dict(cmap="RdBu_r", vmin=-lim, vmax=lim))):
        im = a.imshow(img, **kw)
        a.set_title(f"{title} @ {nm:.0f} nm")
        a.set_xticks([]); a.set_yticks([])
        plt.colorbar(im, ax=a, fraction=0.046)
    if ok.sum() > 10:
        ax[3].hexbin(theirs[ok], ours[ok], gridsize=45, mincnt=1, cmap="viridis")
        hi = float(max(np.nanpercentile(theirs[ok], 99), np.nanpercentile(ours[ok], 99)))
        ax[3].plot([0, hi], [0, hi], "r--", lw=1)
        ax[3].set_xlabel("JPL L2A"); ax[3].set_ylabel("hyperproc")
        ax[3].set_title(f"r={stats['r']:.3f}  RMSE={stats['rmse']:.4f}")
    else:
        ax[3].text(0.5, 0.5, "too few valid pixels", ha="center", va="center")
        ax[3].set_xticks([]); ax[3].set_yticks([])
    fig.suptitle("two independent atmospheric corrections of the same radiance", y=1.03)
    savefig(fig, "03_ac_vs_jpl.png")
    return stats


def figure_spectra(hp, ac, acb, l2a_sub, l2a_brdf, nm):
    """Every product on one axis, which is where the water bands become obvious."""
    import matplotlib.pyplot as plt
    import numpy as np

    series = []
    if ac is not None:
        d = read_product(ac["reflectance"])
        series.append(("hyperproc AC", d.wavelength.values,
                       mean_spectrum(d.reflectance), "C0", "-"))
    if acb is not None:
        d = read_product(acb["reflectance"])
        series.append(("hyperproc AC + BRDF", d.wavelength.values,
                       mean_spectrum(d.reflectance), "C0", "--"))
    series.append(("JPL L2A", l2a_sub.wavelength.values,
                   mean_spectrum(l2a_sub.reflectance), "C1", "-"))
    if l2a_brdf is not None:
        series.append(("JPL L2A + BRDF", l2a_brdf.wavelength.values,
                       mean_spectrum(l2a_brdf.reflectance), "C1", "--"))

    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
    for label, wl, spec, colour, style in series:
        ax[0].plot(wl, spec, style, color=colour, lw=1.3, label=label)
    for lo, hi in ((1340, 1460), (1790, 1960)):          # the water-vapour gaps
        ax[0].axvspan(lo, hi, color="0.88", zorder=0)
    ax[0].axvline(nm, color="0.4", lw=0.8, ls=":")
    ax[0].set_xlabel("wavelength (nm)"); ax[0].set_ylabel("reflectance")
    ax[0].set_title("mean spectrum over the window (grey: water-vapour bands)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

    # the differences, which are what a mean spectrum hides
    base = next((s for s in series if s[0] == "JPL L2A"), None)
    for label, wl, spec, colour, style in series:
        if label == "JPL L2A" or base is None:
            continue
        common = np.interp(base[1], wl, spec)
        ax[1].plot(base[1], common - base[2], style, color=colour, lw=1.2, label=label)
    ax[1].axhline(0, color="0.4", lw=0.8)
    for lo, hi in ((1340, 1460), (1790, 1960)):
        ax[1].axvspan(lo, hi, color="0.88", zorder=0)
    ax[1].set_xlabel("wavelength (nm)"); ax[1].set_ylabel("difference from JPL L2A")
    ax[1].set_title("what each step changed")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    return savefig(fig, "04_spectra.png")


def figure_brdf(before, after, title, filename, nm):
    """Before, after and the difference, for one BRDF route."""
    import matplotlib.pyplot as plt
    import numpy as np

    b = before.reflectance.isel(wavelength=band_at(before, nm)).values
    a_ = after.reflectance.isel(wavelength=band_at(after, nm)).values
    ok = np.isfinite(b) & np.isfinite(a_) & (b > 0.01)
    change = float(np.median((a_[ok] - b[ok]) / b[ok]) * 100) if ok.sum() else float("nan")
    say(f"{title}: median change at {nm:.0f} nm {change:+.2f} %")

    lim = float(np.nanpercentile(np.abs(a_ - b), 98)) or 0.05
    lo, hi = limits(b, a_)                 # one scale across before and after
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.0))
    for axis, img, label, kw in (
            (ax[0], b, "before", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[1], a_, "after", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[2], a_ - b, "after - before",
             dict(cmap="RdBu_r", vmin=-lim, vmax=lim))):
        im = axis.imshow(img, **kw)
        axis.set_title(f"{label} @ {nm:.0f} nm")
        axis.set_xticks([]); axis.set_yticks([])
        plt.colorbar(im, ax=axis, fraction=0.046)
    fig.suptitle(f"{title}  (median change {change:+.2f} %)", y=1.03)
    savefig(fig, filename)
    return change


def figure_quality(q, shares):
    """The bit layer, and the share each flag covers."""
    import matplotlib.pyplot as plt
    import numpy as np
    present = {k: v for k, v in shares.items() if v > 0}
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2),
                           gridspec_kw={"width_ratios": [1, 1.1]})
    im = ax[0].imshow(q.values, cmap="turbo")
    ax[0].set_title("quality bit layer (uint16)")
    ax[0].set_xticks([]); ax[0].set_yticks([])
    plt.colorbar(im, ax=ax[0], fraction=0.046)
    if present:
        names = list(present)
        ax[1].barh(names, [present[n] * 100 for n in names], color="C0")
        ax[1].set_xlabel("percent of pixels")
        ax[1].invert_yaxis()
        ax[1].grid(alpha=0.3, axis="x")
    else:
        ax[1].text(0.5, 0.5, "no flag set anywhere", ha="center", va="center")
    ax[1].set_title("what each flag covers")
    return savefig(fig, "07_quality.png")


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #

def main(argv=None):
    args = parse_args(argv)
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    t_start = time.time()
    import hyperproc as hp
    import matplotlib
    matplotlib.use("Agg")                          # no display on a server

    OUT.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)

    print(f"hyperproc {hp.__version__}  |  python {sys.version.split()[0]}")
    print(f"sensor  {SENSOR}")
    print(f"window  {args.window or 'whole granule'}")
    print(f"data    {DATA}")
    print(f"out     {OUT}")

    summary = {"sensor": SENSOR, "hyperproc": hp.__version__,
               "started": datetime.now().isoformat(timespec="seconds"),
               "window": args.window, "format": args.format,
               "sza_ref": args.sza_ref, "vza_ref": args.vza_ref,
               "diag_nm": args.diag_nm}

    # -- 1. data ----------------------------------------------------------
    l1b_path, l2a_path = find_and_download(args, hp)
    summary["granules"] = {"l1b": l1b_path.name, "l2a": l2a_path.name}
    if args.stage == "download":
        return finish(summary, t_start)

    # -- 2. read and export ------------------------------------------------
    l1b, l2a, l1b_sub, l2a_sub, written, win = read_and_export(
        args, hp, l1b_path, l2a_path)
    summary["exports"] = written
    summary["window_content"] = win
    if not args.no_figures:
        figure_inputs(hp, l1b_sub, l2a_sub, args.diag_nm)
        figure_geometry(l1b_sub)
    if args.stage == "read":
        return finish(summary, t_start)

    # -- 3. atmospheric correction ----------------------------------------
    ac = run_ac(args, hp, l1b_path)
    summary["ac"] = {"reflectance": str(ac["reflectance"])} if ac else None
    if ac and not args.no_figures:
        summary["ac_vs_jpl"] = figure_ac_vs_jpl(ac, l2a, args.diag_nm)
    if args.stage == "ac":
        return finish(summary, t_start)

    # -- 4. BRDF on both routes -------------------------------------------
    step("MODIS BRDF parameters")
    params = fetch_modis(hp, l2a_sub)
    acb = l2a_brdf = None
    if params is not None:
        if ac is not None:
            acb = run_ac_brdf(args, hp, l1b_path, params)
            summary["ac_brdf"] = {"reflectance": str(acb["reflectance"])}
        l2a_brdf, l2a_brdf_path = run_l2a_brdf(args, hp, l2a_sub, params)
        summary["l2a_brdf"] = {"product": str(l2a_brdf_path)}

        step("did the BRDF step do what it should?")
        summary["brdf_verdict"] = judge_brdf(hp, l2a_sub, l2a_brdf, params, args.diag_nm)

    # -- 5. quality --------------------------------------------------------
    q, shares = quality(hp, l2a_sub)
    summary["quality_shares"] = shares

    # -- 6. figures --------------------------------------------------------
    if not args.no_figures:
        step("figures")
        if l2a_brdf is not None:
            summary["l2a_brdf_change_pct"] = figure_brdf(
                l2a_sub, l2a_brdf, "JPL L2A -> BRDF", "05_brdf_l2a.png", args.diag_nm)
        if ac is not None and acb is not None:
            before = read_product(ac["reflectance"])
            after = read_product(acb["reflectance"])
            summary["ac_brdf_change_pct"] = figure_brdf(
                before, after, "hyperproc AC -> BRDF", "06_brdf_ac.png", args.diag_nm)
        figure_quality(q, shares)
        figure_spectra(hp, ac, acb, l2a_sub, l2a_brdf, args.diag_nm)

    return finish(summary, t_start)


def finish(summary, t_start):
    summary["minutes"] = round((time.time() - t_start) / 60, 2)
    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    path = OUT / "summary.json"
    path.write_text(json.dumps(summary, indent=2, default=str))

    step("done")
    say(f"{summary['minutes']:.1f} minutes")
    say(f"products {OUT}")
    figs = sorted(FIGS.glob("*.png"))
    say(f"figures  {len(figs)} in {FIGS}")
    for f in figs:
        say(f"  {f.name}")
    say(f"summary  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
