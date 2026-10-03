#!/usr/bin/env python
"""The pipeline every sensor script runs, with the sensor as a parameter.

Five instruments, one route:

    L1 radiance  --atmospheric-->  reflectance  --BRDF-->  normalised
    L2 reflectance            (the provider's own AC)  --BRDF-->  normalised

and then the comparison that makes running both worthwhile: our retrieval
against the provider's over the same ground, and each BRDF step against its
own input.

What differs between sensors is declared in :class:`SensorConfig` and nothing
else - which file is the radiance, which is the reflectance, whether the two
share a grid, where the data comes from. Keeping that in one table rather than
in five copies of this file is the point: a fix to the pipeline is a fix for
every sensor, and a sensor's quirk is visible as a line of configuration
rather than buried in a fork.

Used by enmap_pipeline.py, desis_pipeline.py, pace_pipeline.py,
prisma_pipeline.py and tanager_pipeline.py. Run those, not this.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
import textwrap
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # py_tests/0_src_code
WORK = HERE                                     # 1_data and 2_outputs sit beside the scripts
PY_TESTS = HERE.parent                          # py_tests
REPO = PY_TESTS.parent                          # the repository root
# where the existing granules live; HYPERPROC_TESTS_DATA overrides it, which a
# copy of these scripts outside the repository needs - REPO is wrong there
TESTS_DATA = Path(os.environ.get("HYPERPROC_TESTS_DATA",
                                 REPO / "tests" / "data")).expanduser()


# --------------------------------------------------------------------------- #
# what differs between sensors                                                 #
# --------------------------------------------------------------------------- #

@dataclass
class SensorConfig:
    """Everything about one instrument that the pipeline needs to know.

    Attributes:
        name: the folder name under 1_data and 2_outputs, and the title on
            every figure.
        l1_glob, l2_glob: how to find the radiance and the reflectance, as
            globs relative to the data folder. Both are also used against
            tests/data when copying.
        l1_open, l2_open: keyword arguments for :func:`hyperproc.open`. PRISMA
            needs ``latlon=True`` on the L1 to get coordinates for a swath.
        window: rows and columns to process. **Which grid those index is the
            sensor's business**: for EnMAP, DESIS, PACE and Tanager the two
            levels share a grid and the window is the same on both; for PRISMA
            the L1 is a swath and the L2D a UTM grid, so ``subset`` says how to
            carry the window across.
        subset: how the window carries from the L1 to the L2.
            ``"isel"`` when both levels share a grid; ``"reproject"`` when the
            L1 is a swath and the L2 a projected grid (PRISMA); ``"detector"``
            when the window indexes the **detector** grid and both levels are
            selected by the ground it covers (EMIT).
        pair: how to find the L2 of the same acquisition from the L1's name.
            Either ``(from, to)`` substrings, or a callable returning a glob -
            PACE needs the second, because CMR prefixes its granule names with
            the collection and the two collections differ, and so does EnMAP,
            whose two levels end in different processing timestamps.
        scene: the acquisition to download, as a glob on the name of the
            first level the archive publishes - the L1, or the L2 where the L1
            is not published (DESIS). The default window was chosen on this
            scene, so pinning it keeps the window over the ground it was meant
            for. ``None`` takes the clearest scene in ``bbox`` and ``date``.
        bbox, date, max_cloud: where and when to search. CMR finds a pinned
            ``scene`` by name alone; DLR's catalogue cannot search by name, so
            EnMAP and DESIS need a box and a day that contain the scene.
        diag_nm: the wavelength every map and comparison uses.
        source: where to get the data - ``"cmr"``, ``"dlr"`` or ``"copy"``.
        search: ``(sensor, l1_level, l2_level)`` for a searchable archive. A
            level hyperproc cannot fetch is named here all the same; the run
            downloads the rest, says why that one is yours to get, and stops.
        note: printed at the start, for anything a user should know up front.
    """
    name: str
    l1_glob: str
    l2_glob: str
    window: dict
    diag_nm: float = 865.0
    l1_open: dict = field(default_factory=dict)
    l2_open: dict = field(default_factory=dict)
    subset: str = "isel"
    source: str = "copy"
    search: tuple | None = None
    pair: tuple | None = None
    scene: str | None = None
    bbox: tuple | None = None
    date: tuple | str | None = None
    max_cloud: float = 20.0
    note: str = ""

    @property
    def data(self):
        return WORK / "1_data" / self.name

    @property
    def out(self):
        return WORK / "2_outputs" / self.name

    @property
    def figs(self):
        return self.out / "figures"


# --------------------------------------------------------------------------- #
# arguments                                                                    #
# --------------------------------------------------------------------------- #

def parse_args(cfg, argv=None):
    y0, y1 = cfg.window["y"]
    x0, x1 = cfg.window["x"]
    p = argparse.ArgumentParser(
        description=f"hyperproc end to end on one {cfg.name} scene",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)

    g = p.add_argument_group("what to process")
    g.add_argument("--window", nargs=4, type=int, metavar=("Y0", "Y1", "X0", "X1"),
                   default=[y0, y1, x0, x1],
                   help=f"rows and columns (default {y0} {y1} {x0} {x1}). "
                        f"Step 2 reports what the window actually contains, so "
                        f"a window of open water is visible before the "
                        f"expensive part. Pass 0 0 0 0 for the whole scene")
    g.add_argument("--workers", type=int, default=20,
                   help="cores for the ISOFIT retrieval (default 20)")
    g.add_argument("--sza-ref", default="45.0",
                   help="sun zenith to normalise to, or 'observed' (default 45)")
    g.add_argument("--vza-ref", type=float, default=0.0)
    g.add_argument("--diag-nm", type=float, default=cfg.diag_nm,
                   help=f"wavelength for every map and comparison "
                        f"(default {cfg.diag_nm:.0f})")

    g = p.add_argument_group("where the data comes from")
    g.add_argument("--source", choices=["auto", "download", "copy"], default="auto",
                   help=f"auto (default) downloads every level the archive "
                        f"publishes and stops to say what it does not; copy "
                        f"takes the scene from tests/data instead. This "
                        f"sensor's route is '{cfg.source}'")
    g.add_argument("--accept-dlr-policy", action="store_true",
                   help="agree to DLR's Acceptable Usage Policy when it is "
                        "waiting on your account (EnMAP, DESIS). The first "
                        "download stops and says where to read it; read it, "
                        "then rerun with this")

    g = p.add_argument_group("how far to go")
    g.add_argument("--stage", choices=["data", "read", "ac", "brdf", "all"],
                   default="all")
    g.add_argument("--format", choices=["GTiff", "ENVI"], default="GTiff")
    g.add_argument("--no-figures", action="store_true")

    args = p.parse_args(argv)
    if args.window == [0, 0, 0, 0]:
        args.window = None
    else:
        a, b, c, d = args.window
        args.window = {"y": (a, b), "x": (c, d)}
    args.sza_ref = "observed" if args.sza_ref == "observed" else float(args.sza_ref)
    return args


# --------------------------------------------------------------------------- #
# small helpers                                                                #
# --------------------------------------------------------------------------- #

STEP = 0


def step(title):
    global STEP
    STEP += 1
    print(f"\n{'=' * 78}\n{STEP}. {title}\n{'=' * 78}", flush=True)


def say(*parts):
    print("   ", *parts, flush=True)


def work_dir_for(cfg, window):
    """ISOFIT's working directory, one per window.

    ``process`` deliberately reuses a retrieval it finds here, which is what
    makes the AC+BRDF run take seconds rather than minutes. Sharing one folder
    between two windows therefore reuses the *wrong* retrieval, silently: same
    numbers, same reported runtime, painted onto different ground.
    """
    if window is None:
        return cfg.out / "02_ac" / "isofit_full"
    y0, y1 = window["y"]
    x0, x1 = window["x"]
    return cfg.out / "02_ac" / f"isofit_win{y0}-{y1}_{x0}-{x1}"


def raster_grid(path):
    import numpy as np
    import rasterio
    with rasterio.open(path) as src:
        tr = src.transform
        return (tr.c + (np.arange(src.width) + 0.5) * tr.a,
                tr.f + (np.arange(src.height) + 0.5) * tr.e)


def same_ground(ds, x, y):
    """The part of ``ds`` covering those coordinates, to within one pixel."""
    tol = abs(float(ds.x[1] - ds.x[0]))
    return ds.sel(x=x, y=y, method="nearest", tolerance=tol)


def read_product(path, var="reflectance", geometry_from=None, sensor=""):
    """Read a product this package wrote back into a dataset.

    ``hyperproc.open`` does not accept its own products: they carry no
    geometry, so a correction needing angles would silently get none. Taking
    the angles from the granule, **by coordinate**, is what makes the reloaded
    cube usable again.
    """
    import numpy as np
    import rasterio
    import xarray as xr

    with rasterio.open(path) as src:
        envi = src.tags(ns="ENVI")
        if "wavelength" in envi:
            wl = np.array([float(v) for v in envi["wavelength"].strip("{}").split(",")])
        else:
            wl = np.array([float(d.split()[0]) for d in src.descriptions])
        cube = src.read().astype("float32")
        if src.nodata is not None:
            cube[cube == src.nodata] = np.nan
        tr, crs, ny, nx = src.transform, str(src.crs), src.height, src.width

    ds = xr.Dataset(
        {var: (("y", "x", "wavelength"), np.moveaxis(cube, 0, -1))},
        coords={"wavelength": wl,
                "x": tr.c + (np.arange(nx) + 0.5) * tr.a,
                "y": tr.f + (np.arange(ny) + 0.5) * tr.e},
        attrs={"crs": crs, "transform": tuple(tr.to_gdal()), "sensor": sensor,
               "stem": Path(path).stem, "units": "1"})
    if geometry_from is not None:
        g = same_ground(geometry_from, ds.x.values, ds.y.values)
        for layer in ("sza", "saa", "vza", "vaa", "raa"):
            if layer in g:
                ds[layer] = (("y", "x"), g[layer].values)
    return ds


def for_export(hp, ds):
    """A dataset ready to write: a swath is projected first, a grid passes through.

    GeoTIFF and ENVI both need a map projection. A swath carries per-pixel
    latitude and longitude instead, so it is resampled onto a regular grid -
    PACE's two levels and PRISMA's L1 are all swaths, and `to_geotiff` refuses
    them with an explanation rather than writing a file that claims a grid it
    does not have.
    """
    if ds.attrs.get("crs"):
        return ds
    say("  swath with no CRS; projecting it onto a regular grid for export")
    return hp.georeference(ds)


def band_at(ds, nm):
    import numpy as np
    return int(np.argmin(np.abs(ds.wavelength.values - nm)))


def mean_spectrum(cube, max_pixels=20000):
    import numpy as np
    a = cube.values if hasattr(cube, "values") else cube
    flat = a.reshape(-1, a.shape[-1])
    if flat.shape[0] > max_pixels:
        flat = flat[np.linspace(0, flat.shape[0] - 1, max_pixels).astype(int)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return np.nanmean(flat, axis=0)


def limits(*images, lo=2, hi=98):
    """Colour limits from the data, shared across every image given.

    Hard-coded limits are how a dark scene renders as a black rectangle.
    Passing several images together keeps a before/after pair on one scale, so
    a difference in the picture is a difference in the data.
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


def savefig(cfg, fig, name):
    import matplotlib.pyplot as plt
    cfg.figs.mkdir(parents=True, exist_ok=True)
    path = cfg.figs / name
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    say(f"figure -> {path.relative_to(WORK)}")
    return path


def describe_window(ds, var=None):
    """What is in the window: bright or dark, vegetated or not, water or land.

    Worth a few seconds before anything expensive. The BRDF route borrows its
    angular shape from MODIS *land* kernels, so a window of open water produces
    numbers that look like results and mean very little.
    """
    import numpy as np
    var = var or ("reflectance" if "reflectance" in ds else None)
    if var is None or var not in ds:
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


# --------------------------------------------------------------------------- #
# 1. get the data                                                              #
# --------------------------------------------------------------------------- #

def copy_from_tests(cfg):
    """Copy the existing granule out of tests/data.

    PRISMA and Tanager have no public search API at all, so for those the
    scene already on disk is the scene. Every other sensor comes here only
    when ``--source copy`` asks.
    """
    cfg.data.mkdir(parents=True, exist_ok=True)
    copied = []
    for glob in (cfg.l1_glob, cfg.l2_glob):
        # the stem without the level marker finds the siblings too - an EnMAP
        # GeoTIFF is useless without its METADATA.XML next to it
        for src in sorted(TESTS_DATA.glob(glob)):
            stem = src.name.split("-SPECTRAL_IMAGE")[0].split(".")[0]
            folder = src.parent
            for mate in sorted(folder.glob(f"{stem}*")):
                dest = cfg.data / mate.name
                if dest.exists() and dest.stat().st_size == mate.stat().st_size:
                    continue
                shutil.copy2(mate, dest)
                copied.append(dest)
    if copied:
        total = sum(p.stat().st_size for p in copied) / 1e9
        say(f"copied {len(copied)} files ({total:.2f} GB) from tests/data")
    elif sorted(cfg.data.glob(Path(cfg.l1_glob).name)):
        say("everything was already in place")
    else:
        # Nothing copied and nothing to copy to: tests/data holds the granules
        # the published repository does not carry. Saying "already in place"
        # here would contradict the refusal three lines later.
        say(f"nothing to copy: {TESTS_DATA} has no {cfg.name} scene")
        say("  the repository ships no granules; set HYPERPROC_TESTS_DATA to "
            f"a folder that has them, or put the scene in {cfg.data} yourself")
    return copied


def ask_for_credentials(hp, sensor, level) -> bool:
    """Ask at the terminal for the credential this collection needs.

    Set in this process's environment and nowhere else. Nothing is written to
    disk, so the next run asks again - that is the trade for leaving no file
    behind. ``~/.netrc`` or the environment variables avoid the prompt.

    Asks only when there is a keyboard. Under nbconvert, cron or a pipe,
    ``stdin`` is not a terminal and this returns False rather than hanging on
    an ``input()`` nobody can answer.

    Returns True when hyperproc can see a credential afterwards.
    """
    import getpass

    sensor, level, coll = hp.archive.resolve(sensor, level)
    who, need = hp.archive.BACKENDS[coll.backend]
    if not sys.stdin.isatty():
        return False

    say(f"{who} needs {need}")
    if coll.backend == "cmr":
        user = input("    Earthdata username (blank to skip): ").strip()
        if not user:
            return False
        os.environ["EARTHDATA_USERNAME"] = user
        os.environ["EARTHDATA_PASSWORD"] = getpass.getpass("    Earthdata password: ")
    elif coll.backend == "dlr":
        user = input(f"    {sensor} username (blank to skip): ").strip()
        if not user:
            return False
        os.environ[f"{sensor}_USERNAME"] = user
        os.environ[f"{sensor}_PASSWORD"] = getpass.getpass(f"    {sensor} password: ")
    elif coll.backend == "neon":
        token = getpass.getpass("    NEON API token (blank to skip): ").strip()
        if not token:
            return False
        os.environ["NEON_TOKEN"] = token
    else:
        return False

    ok = hp.archive.can_download(sensor, level)
    say("credentials accepted for this run" if ok else "still nothing usable")
    return ok


def why_not_fetchable(hp, sensor, level):
    """hyperproc's own reason it cannot fetch a level, or None if it can.

    Asked of the package rather than written here, so what gets printed is
    what hyperproc says - which makes the run a check of that message too.
    """
    try:
        hp.archive.resolve(sensor, level)
    except ValueError as exc:
        return str(exc)
    return None


def find_granules(cfg, hp, level, pattern=None, near=None):
    """Granules of ``level`` named like ``pattern``, else the configured search.

    CMR searches by name. DLR's STAC cannot, so there the search runs over a
    place and a day - those of ``near``, the granule being matched, else the
    configured box and dates - and the names are filtered here.
    """
    sensor = cfg.search[0]
    if pattern and hp.archive.resolve(sensor, level)[2].backend == "cmr":
        return list(hp.search(sensor, level, granule_name=pattern, count=10,
                              verbose=False))
    if near is not None and near.bbox and near.time:
        box, when = near.bbox, near.time.strftime("%Y-%m-%d")
    else:
        box, when = cfg.bbox, cfg.date
    if box is None:
        say(f"  no bbox to search {sensor} {level} with; set one in the config")
        return []
    hits = hp.search(sensor, level, bbox=tuple(box), date=when,
                     cloud=None if pattern else (0, cfg.max_cloud),
                     count=50 if pattern else 20, verbose=pattern is None)
    return [g for g in hits if pattern is None or fnmatch.fnmatch(g.name, pattern)]


def download_scene(cfg, hp, args, levels):
    """Fetch one acquisition at every level in ``levels``, matched by name.

    The comparison at the end only means anything if the L1 we correct and the
    L2 we compare it against are the same overpass. Names make that checkable:
    the scene is chosen on the first level and every other level is found from
    its name, rather than by searching the same box again and hoping.
    """
    sensor = cfg.search[0]
    first, rest = levels[0], levels[1:]
    if cfg.scene:
        say(f"looking for {cfg.scene} ({sensor} {first})")
        hits = find_granules(cfg, hp, first, cfg.scene)
    else:
        say(f"searching {cfg.bbox} {cfg.date} for a clear scene")
        hits = find_granules(cfg, hp, first)
    if not hits:
        say("  nothing in the archive matches")
        return None
    pick = min(hits, key=lambda g: (g.cloud if g.cloud is not None else 100,
                                    g.size_mb or 0))
    cloud = f", {pick.cloud:.0f}% cloud" if pick.cloud is not None else ""
    size = f", {pick.size_mb:,.0f} MB" if pick.size_mb else ""
    say(f"chosen {pick.name}{cloud}{size}")

    want = [pick]
    for level in rest:
        if cfg.pair is None:
            say(f"no pair= in the config, so nothing finds the {level} of {pick.name}")
            return None
        pattern = (cfg.pair(pick.name) if callable(cfg.pair)
                   else pick.name.replace(*cfg.pair))
        mate = find_granules(cfg, hp, level, pattern, near=pick)
        if not mate:
            say(f"the matching {level} ({pattern}) is not in the archive")
            return None
        say(f"its {level}  {mate[0].name}")
        want.append(mate[0])

    # DLR asks each account once to agree to its usage policy. Agreeing is the
    # user's to do, so it is a flag and never a default.
    extra = ({"accept_policy": True}
             if args.accept_dlr_policy
             and hp.archive.resolve(sensor, first)[2].backend == "dlr" else {})
    hp.download(want, cfg.data, workers=4, **extra)
    return want


def fetch_or_stop(cfg, args, hp, levels):
    """Download ``levels``, or exit saying why not. Never falls back to a copy."""
    sensor = cfg.search[0]
    if not (hp.archive.can_download(sensor, levels[0])
            or ask_for_credentials(hp, sensor, levels[0])):
        backend = hp.archive.resolve(sensor, levels[0])[2].backend
        who, need = hp.archive.BACKENDS[backend]
        say(f"no credentials for {who}; it needs {need}")
        if backend == "cmr":
            say('  once per machine: python -c "import earthaccess; '
                'earthaccess.login(persist=True)"')
        elif backend == "dlr":
            say(f"  then set {sensor}_USERNAME and {sensor}_PASSWORD, or put the "
                f"account in ~/.netrc for download.geoservice.dlr.de")
        if not sys.stdin.isatty():
            say("  no keyboard here, so nothing was asked")
        sys.exit(f"{cfg.name}: nothing downloaded without credentials "
                 f"(--source copy takes tests/data instead)")

    say(f"downloading from the archive ({sensor} {' and '.join(levels)})")
    try:
        got = download_scene(cfg, hp, args, levels)
    except Exception as exc:
        hint = ""
        if "policy" in str(exc).lower() and not args.accept_dlr_policy:
            hint = "\n    once you have read it, rerun with --accept-dlr-policy"
        sys.exit(f"{cfg.name}: the download did not work\n"
                 f"    {type(exc).__name__}: {exc}{hint}")
    if got is None:
        sys.exit(f"{cfg.name}: could not find the scene at {' and '.join(levels)}")


def acquire(cfg, args, hp):
    """Put the L1 and L2 of one scene into 1_data/<sensor>/.

    Every level an archive publishes is downloaded. A level none publishes -
    DESIS radiance - is named with hyperproc's reason and the run stops there,
    to start once you have put it in place. Nothing falls back to tests/data
    unless ``--source copy`` asks for it: a run meant to test the downloads
    that quietly copied instead would pass without downloading anything.
    """
    step(f"get the {cfg.name} scene")
    cfg.data.mkdir(parents=True, exist_ok=True)
    sensor, l1_level, l2_level = cfg.search or (cfg.name, "L1", "L2")
    glob_of = {l1_level: cfg.l1_glob, l2_level: cfg.l2_glob}

    def on_disk():
        return {lv: sorted(cfg.data.glob(Path(g).name)) for lv, g in glob_of.items()}

    have = on_disk()
    if all(have.values()):
        say(f"already there: {have[l1_level][0].name}")
        say(f"              {have[l2_level][0].name}")
        return have[l1_level][0], have[l2_level][0]

    route = cfg.source if args.source == "auto" else args.source
    if route == "copy" or not cfg.search:
        if cfg.source == "copy" and cfg.search:
            say(f"no archive publishes this {cfg.name} scene, so it comes "
                f"from tests/data")
        elif cfg.source == "copy":
            say(f"{cfg.name} has no public search API, so the scene in "
                f"tests/data is the scene")
        copy_from_tests(cfg)
    else:
        fetchable = [lv for lv in glob_of if why_not_fetchable(hp, sensor, lv) is None]
        if fetchable and not all(have[lv] for lv in fetchable):
            fetch_or_stop(cfg, args, hp, fetchable)
        elif fetchable:
            say(f"{' and '.join(fetchable)} already there")

    have = on_disk()
    missing = [lv for lv in glob_of if not have[lv]]
    if missing:
        present = [have[lv][0] for lv in glob_of if have[lv]]
        for lv in missing:
            why = why_not_fetchable(hp, sensor, lv)
            if why is None and route != "copy":
                say(f"{sensor} {lv} was downloaded, but nothing in {cfg.data} "
                    f"matches {Path(glob_of[lv]).name} - the archive names its "
                    f"files differently from the glob in the config")
                continue
            print()
            say(f"{sensor} {lv} is not here - you need to get it yourself"
                + (", because:" if why else ""))
            for line in textwrap.wrap(why or "", width=72, break_long_words=False,
                                      break_on_hyphens=False):
                say(f"    {line}")
            if present:
                same = Path(present[0].name.split("-SPECTRAL_IMAGE")[0]).stem
                say(f"  it must be the same acquisition as {same}")
                say("    - another date or tile and the comparison is of two "
                    "different scenes")
            say(f"  put it in {cfg.data}")
            say(f"    as {Path(glob_of[lv]).name}, with every file that came "
                f"with it beside it")
        sys.exit(f"{cfg.name}: waiting for {' and '.join(missing)}; "
                 f"rerun once {'it is' if len(missing) == 1 else 'they are'} "
                 f"in {cfg.data}")

    l1, l2 = have[l1_level], have[l2_level]
    for f in sorted(cfg.data.iterdir()):
        if f.is_file() and f.stat().st_size > 1e7:
            say(f"  {f.name}  {f.stat().st_size / 1e9:.2f} GB")
    return l1[0], l2[0]


# --------------------------------------------------------------------------- #
# 2. read and export                                                           #
# --------------------------------------------------------------------------- #

def subset_l2(cfg, args, l1, l2):
    """The part of the L2 that the L1 window covers.

    Four of the five sensors deliver both levels on one grid, where the window
    is simply the same rows and columns. PRISMA does not: its L1 is a swath and
    its L2D a UTM grid, so the same numbers would land somewhere else entirely
    and the comparison would be of two different places.
    """
    import numpy as np
    if args.window is None:
        return l1, l2
    w = args.window
    if cfg.subset == "detector":
        # The window counts rows and columns on the DETECTOR grid, which is
        # where the retrieval runs. The ortho grid is a different grid, so the
        # same numbers there land somewhere else - on an EMIT granule, out at
        # sea. Take the ground the detector window covers and select that.
        import hyperproc as hp
        det = hp.open(cfg._l1_path, ortho=False, **cfg.l1_open)
        d = det.isel(y=slice(*w["y"]), x=slice(*w["x"]))
        west, east = float(d.lon.min()), float(d.lon.max())
        south, north = float(d.lat.min()), float(d.lat.max())
        say(f"the detector window covers {west:.3f}..{east:.3f} E, "
            f"{south:.3f}..{north:.3f} N")
        box = dict(x=slice(west, east), y=slice(north, south))   # y runs N to S
        return l1.sel(**box), l2.sel(**box)

    if cfg.subset == "isel":
        return (l1.isel(y=slice(*w["y"]), x=slice(*w["x"])),
                l2.isel(y=slice(*w["y"]), x=slice(*w["x"])))

    from pyproj import Transformer
    sub1 = l1.isel(y=slice(*w["y"]), x=slice(*w["x"]))
    t = Transformer.from_crs("EPSG:4326", l2.attrs["crs"], always_xy=True)
    xs, ys = t.transform(sub1.lon.values.ravel(), sub1.lat.values.ravel())
    y_slice = (slice(np.nanmax(ys), np.nanmin(ys)) if float(l2.y[0]) > float(l2.y[-1])
               else slice(np.nanmin(ys), np.nanmax(ys)))
    sub2 = l2.sel(x=slice(np.nanmin(xs), np.nanmax(xs)), y=y_slice)
    say(f"the L1 window covers {np.nanmin(xs):.0f}..{np.nanmax(xs):.0f} E, "
        f"{np.nanmin(ys):.0f}..{np.nanmax(ys):.0f} N in the L2's CRS")
    return sub1, sub2


def read_and_export(cfg, args, hp, l1_path, l2_path):
    step("read both levels, export both formats")
    say("sniff:", hp.sniff(l1_path), "|", hp.sniff(l2_path))
    l1 = hp.open(l1_path, **cfg.l1_open)
    l2 = hp.open(l2_path, **cfg.l2_open)

    for name, ds in ((f"L1 {hp.main_var(l1)}", l1), ("L2", l2)):
        say(f"{name:16s} {dict(ds.sizes)}  var={hp.main_var(ds)}  "
            f"units={ds.attrs.get('units')}  crs={str(ds.attrs.get('crs'))[:24]}")

    l1_sub, l2_sub = subset_l2(cfg, args, l1, l2)
    say(f"window  L1 {dict(l1_sub.sizes)}   L2 {dict(l2_sub.sizes)}")
    content = describe_window(l2_sub)
    say("geometry on the L1:",
        ", ".join(v for v in ("sza", "saa", "vza", "vaa", "raa", "elev") if v in l1)
        or "none")

    out = cfg.out / "01_read"
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for label, ds in ((f"l1_{hp.main_var(l1_sub)}", l1_sub),
                      (f"l2_{hp.main_var(l2_sub)}", l2_sub)):
        t0 = time.time()
        grid = for_export(hp, ds)
        tif = hp.to_geotiff(grid, out / f"{label}.tif", overviews=True)
        img = hp.to_envi(grid, out / f"{label}.img", interleave="bil")
        hp.bands_to_csv(grid, out / f"{label}_bands.csv")
        written[label] = {"GTiff": str(tif), "ENVI": str(img)}
        say(f"{label:18s} GeoTIFF {tif.stat().st_size / 1e6:7.1f} MB   "
            f"ENVI {img.stat().st_size / 1e6:7.1f} MB   ({time.time() - t0:.1f} s)")
    return l1, l2, l1_sub, l2_sub, written, content


# --------------------------------------------------------------------------- #
# 3. corrections                                                               #
# --------------------------------------------------------------------------- #

def run_ac(cfg, args, hp, l1_path):
    step(f"L1 -> surface reflectance (ISOFIT), {cfg.name}")
    from hyperproc.atmos import check, process

    report = check(engines=("sRTMnet",))
    if not report["ok"]:
        say("ISOFIT assets are not in place; run hyperproc-atmos-setup --check")
        return None

    work = work_dir_for(cfg, args.window)
    say(f"work dir {work.name}"
        f"{'  (reusing the retrieval found there)' if work.exists() else ''}")
    t0 = time.time()
    ac = process(l1_path, cfg.out / "02_ac", work_dir=work, stages=("ac",),
                 workers=args.workers, window=args.window, format=args.format,
                 layers=("aot550", "h2o"), overviews=True, verbose=True)
    say(f"{(time.time() - t0) / 60:.1f} min -> {Path(ac['reflectance']).name}")
    prov = json.loads(Path(ac["provenance"]).read_text())
    say(f"grid {prov['grid']['shape']}  isofit v{prov['isofit']['version']}, "
        f"{prov['isofit']['seconds']} s")
    return ac


def fetch_modis(cfg, hp, l2_sub):
    from hyperproc.correct import mcd43
    try:
        params = mcd43.fetch(ds=l2_sub, out_dir=cfg.out / "03_ac_brdf" / "mcd43",
                             verbose=True)
    except Exception as exc:
        say(f"MODIS parameters unavailable: {type(exc).__name__}: {exc}")
        say("  the BRDF route needs Earth Engine: pip install 'hyperproc[brdf]'")
        say("  then: earthengine authenticate")
        return None
    say(f"MODIS {params.shape} at {abs(params.transform[0]) * 111320:.0f} m, "
        f"date {params.date}, {params.coverage() * 100:.0f} % of cells retrieved")
    return params


def run_ac_brdf(cfg, args, hp, l1_path, params):
    step("L1 -> reflectance -> BRDF, in one call")
    from hyperproc.atmos import process
    t0 = time.time()
    acb = process(l1_path, cfg.out / "03_ac_brdf",
                  work_dir=work_dir_for(cfg, args.window), stages=("ac", "brdf"),
                  workers=args.workers, window=args.window, format=args.format,
                  overviews=True,
                  brdf=dict(params=params, sza_ref=args.sza_ref,
                            vza_ref=args.vza_ref, spectral="nearest", fill="none"),
                  verbose=True)
    say(f"{(time.time() - t0) / 60:.1f} min -> {Path(acb['reflectance']).name}")
    say("the retrieval was reused; only the BRDF step and the export ran")
    return acb


def run_l2_brdf(cfg, args, hp, l2_sub, params):
    step("L2 reflectance -> BRDF")
    t0 = time.time()
    brdf = hp.correct.nbar(l2_sub, params=params, sza_ref=args.sza_ref,
                           vza_ref=args.vza_ref, spectral="nearest", fill="none",
                           cache_dir=cfg.out / "03_ac_brdf" / "mcd43")
    say(f"built in {time.time() - t0:.1f} s (lazy); stem {brdf.attrs['stem']}")
    for k, v in brdf.attrs.items():
        if k.startswith("brdf_"):
            say(f"  {k:24s} {v}")

    out = cfg.out / "04_l2_brdf"
    out.mkdir(parents=True, exist_ok=True)
    slim = brdf.drop_vars([v for v in ("c_factor", "modis_band") if v in brdf.variables])
    slim = for_export(hp, slim)      # PACE's L2 is a swath; a raster needs a grid
    kw = {"overviews": True} if args.format == "GTiff" else {}
    t0 = time.time()
    p = hp.to_raster(slim, out / f"{brdf.attrs['stem']}{hp.FORMATS[args.format]}",
                     format=args.format, **kw)
    hp.bands_to_csv(slim, out / f"{brdf.attrs['stem']}_bands.csv")
    say(f"wrote {p.name} ({p.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.1f} s")
    return brdf, p


def judge_brdf(before, after, params, nm):
    """Two measurable questions, either of which may answer 'cannot tell here'.

    A small window often spans too little view angle to show any trend, and
    that is a fact about the window rather than a failure of the correction.
    """
    from hyperproc.correct import cfactor
    out = {}
    try:
        prof = cfactor.view_profile(before, after, wavelength=nm, step=0.25, stride=3)
        out["view_profile"] = {k: float(v) for k, v in prof.items()
                               if isinstance(v, (int, float))}
        say(f"view-angle slope at {nm:.0f} nm: {prof['slope_before'] * 1000:+.3f} -> "
            f"{prof['slope_after'] * 1000:+.3f} e-3 per degree over "
            f"{prof['vza_span']:.2f} deg")
    except ValueError as exc:
        say("view profile not available:", exc)
    try:
        agree = cfactor.model_agreement(before, params.masked(), wavelength=nm, stride=2)
        out["model_agreement"] = {"r": float(agree["r"]),
                                  "r_flipped": float(agree["r_flipped"]),
                                  "verdict": agree["verdict"]}
        say(f"model agreement r={agree['r']:+.3f} -> {agree['verdict']}")
    except ValueError as exc:
        say("model agreement not testable:", exc)
    return out


def quality(hp, l2_sub):
    step("quality flags")
    import numpy as np
    q = hp.quality_flags(l2_sub, derive=("fill", "terrain_shadow"))
    meanings = q.attrs.get("flag_meanings", "").split()
    masks = q.attrs.get("flag_masks", "")
    masks = masks.split() if isinstance(masks, str) else list(masks)
    shares = {name: float(((q.values & int(bit)) > 0).mean())
              for name, bit in zip(meanings, masks)}
    for name, frac in sorted(shares.items(), key=lambda kv: -kv[1]):
        if frac > 0:
            say(f"{name:18s} {frac * 100:5.1f} %")
    clear = hp.quality_apply(l2_sub, q,
                             drop=("fill", "cloud", "cloud_shadow", "cirrus"))
    kept = float(np.isfinite(clear[hp.main_var(clear)].isel(wavelength=0)).mean())
    say(f"{kept * 100:.1f} % of pixels survive the default mask")
    return q, shares


# --------------------------------------------------------------------------- #
# figures                                                                      #
# --------------------------------------------------------------------------- #

def figure_inputs(cfg, hp, l1_sub, l2_sub, nm):
    import matplotlib.pyplot as plt
    v1 = hp.main_var(l1_sub)
    a = l1_sub[v1].isel(wavelength=band_at(l1_sub, nm)).values
    b = l2_sub.reflectance.isel(wavelength=band_at(l2_sub, nm)).values
    alo, ahi = limits(a)
    blo, bhi = limits(b)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    for axis, img, title, kw in (
            (ax[0], a, f"L1 {v1} @ {nm:.0f} nm", dict(cmap="magma", vmin=alo, vmax=ahi)),
            (ax[1], b, f"L2 reflectance @ {nm:.0f} nm",
             dict(cmap="gray", vmin=blo, vmax=bhi))):
        im = axis.imshow(img, **kw)
        axis.set_title(title)
        axis.set_xticks([]); axis.set_yticks([])
        plt.colorbar(im, ax=axis, fraction=0.046)
    fig.suptitle(f"{cfg.name}: the two levels this script starts from", y=1.02)
    return savefig(cfg, fig, "01_inputs.png")


def figure_geometry(cfg, l1_sub):
    import matplotlib.pyplot as plt
    layers = [v for v in ("sza", "vza", "raa", "saa", "vaa", "elev") if v in l1_sub]
    if not layers:
        say("no geometry layers on this product; skipping the geometry figure")
        return None
    n = len(layers)
    fig, ax = plt.subplots(1, n, figsize=(3.4 * n, 3.6))
    ax = [ax] if n == 1 else list(ax)
    for axis, name in zip(ax, layers):
        im = axis.imshow(l1_sub[name].values, cmap="viridis")
        axis.set_title(f"{name}  ({l1_sub[name].attrs.get('units', '')})")
        axis.set_xticks([]); axis.set_yticks([])
        plt.colorbar(im, ax=axis, fraction=0.046)
    fig.suptitle(f"{cfg.name}: observation geometry", y=1.04)
    return savefig(cfg, fig, "02_geometry.png")


def figure_ac_vs_provider(cfg, ac, l2, nm):
    """Our retrieval against the provider's, as maps and as a scatter."""
    import matplotlib.pyplot as plt
    import numpy as np
    import rasterio

    with rasterio.open(ac["reflectance"]) as src:
        wl = np.array([float(d.split()[0]) for d in src.descriptions])
        ours = src.read(int(np.argmin(np.abs(wl - nm))) + 1).astype("float32")
        if src.nodata is not None:
            ours[ours == src.nodata] = np.nan
    xs, ys = raster_grid(ac["reflectance"])
    try:
        theirs = same_ground(
            l2.reflectance.isel(wavelength=band_at(l2, nm)), xs, ys).values
    except Exception as exc:
        say(f"cannot line the two up by coordinate ({exc}); skipping this figure")
        return {}

    ok = np.isfinite(ours) & np.isfinite(theirs) & (ours > 0) & (theirs > 0)
    stats = {}
    if ok.sum() > 10:
        d = ours[ok] - theirs[ok]
        stats = {"n": int(ok.sum()), "median_difference": float(np.median(d)),
                 "rmse": float(np.sqrt(np.mean(d ** 2))),
                 "r": float(np.corrcoef(ours[ok], theirs[ok])[0, 1])}
        say(f"at {nm:.0f} nm over {stats['n']:,} pixels: "
            f"median {stats['median_difference']:+.4f}, RMSE {stats['rmse']:.4f}, "
            f"r {stats['r']:.4f}")

    lim = float(np.nanpercentile(np.abs(ours - theirs), 98)) or 0.02
    lo, hi = limits(ours, theirs)
    fig, ax = plt.subplots(1, 4, figsize=(19, 4.0))
    for axis, img, title, kw in (
            (ax[0], ours, "hyperproc + ISOFIT", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[1], theirs, f"{cfg.name} provider L2", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[2], ours - theirs, "ours - provider",
             dict(cmap="RdBu_r", vmin=-lim, vmax=lim))):
        im = axis.imshow(img, **kw)
        axis.set_title(f"{title} @ {nm:.0f} nm")
        axis.set_xticks([]); axis.set_yticks([])
        plt.colorbar(im, ax=axis, fraction=0.046)
    if ok.sum() > 10:
        ax[3].hexbin(theirs[ok], ours[ok], gridsize=45, mincnt=1, cmap="viridis")
        top = float(max(np.nanpercentile(theirs[ok], 99), np.nanpercentile(ours[ok], 99)))
        ax[3].plot([0, top], [0, top], "r--", lw=1)
        ax[3].set_xlabel("provider L2"); ax[3].set_ylabel("hyperproc")
        ax[3].set_title(f"r={stats['r']:.3f}  RMSE={stats['rmse']:.4f}")
    else:
        ax[3].text(0.5, 0.5, "too few valid pixels", ha="center", va="center")
    fig.suptitle(f"{cfg.name}: two independent atmospheric corrections "
                 f"of the same radiance", y=1.03)
    savefig(cfg, fig, "03_ac_vs_provider.png")
    return stats


def figure_brdf(cfg, before, after, title, filename, nm):
    import matplotlib.pyplot as plt
    import numpy as np
    b = before.reflectance.isel(wavelength=band_at(before, nm)).values
    a = after.reflectance.isel(wavelength=band_at(after, nm)).values
    ok = np.isfinite(b) & np.isfinite(a) & (b > 0.01)
    change = float(np.median((a[ok] - b[ok]) / b[ok]) * 100) if ok.sum() else float("nan")
    say(f"{title}: median change at {nm:.0f} nm {change:+.2f} %")
    lim = float(np.nanpercentile(np.abs(a - b), 98)) or 0.05
    lo, hi = limits(b, a)
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.0))
    for axis, img, label, kw in (
            (ax[0], b, "before", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[1], a, "after", dict(cmap="gray", vmin=lo, vmax=hi)),
            (ax[2], a - b, "after - before", dict(cmap="RdBu_r", vmin=-lim, vmax=lim))):
        im = axis.imshow(img, **kw)
        axis.set_title(f"{label} @ {nm:.0f} nm")
        axis.set_xticks([]); axis.set_yticks([])
        plt.colorbar(im, ax=axis, fraction=0.046)
    fig.suptitle(f"{cfg.name}: {title}  (median change {change:+.2f} %)", y=1.03)
    savefig(cfg, fig, filename)
    return change


def figure_spectra(cfg, hp, ac, acb, l2_sub, l2_brdf, nm):
    import matplotlib.pyplot as plt
    import numpy as np
    series = []
    if ac is not None:
        d = read_product(ac["reflectance"], sensor=cfg.name)
        series.append(("hyperproc AC", d.wavelength.values,
                       mean_spectrum(d.reflectance), "C0", "-"))
    if acb is not None:
        d = read_product(acb["reflectance"], sensor=cfg.name)
        series.append(("hyperproc AC + BRDF", d.wavelength.values,
                       mean_spectrum(d.reflectance), "C0", "--"))
    series.append(("provider L2", l2_sub.wavelength.values,
                   mean_spectrum(l2_sub.reflectance), "C1", "-"))
    if l2_brdf is not None:
        series.append(("provider L2 + BRDF", l2_brdf.wavelength.values,
                       mean_spectrum(l2_brdf.reflectance), "C1", "--"))

    fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
    for label, wl, spec, colour, style in series:
        ax[0].plot(wl, spec, style, color=colour, lw=1.3, label=label)
    for lo, hi in ((1340, 1460), (1790, 1960)):
        for a in ax:
            a.axvspan(lo, hi, color="0.88", zorder=0)
    ax[0].axvline(nm, color="0.4", lw=0.8, ls=":")
    ax[0].set_xlabel("wavelength (nm)"); ax[0].set_ylabel("reflectance")
    ax[0].set_title("mean spectrum (grey: water-vapour bands)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

    base = next((s for s in series if s[0] == "provider L2"), None)
    for label, wl, spec, colour, style in series:
        if label == "provider L2" or base is None:
            continue
        ax[1].plot(base[1], np.interp(base[1], wl, spec) - base[2], style,
                   color=colour, lw=1.2, label=label)
    ax[1].axhline(0, color="0.4", lw=0.8)
    ax[1].set_xlabel("wavelength (nm)"); ax[1].set_ylabel("difference from provider L2")
    ax[1].set_title("what each step changed")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    fig.suptitle(cfg.name, y=1.02)
    return savefig(cfg, fig, "04_spectra.png")


def figure_quality(cfg, q, shares):
    import matplotlib.pyplot as plt
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
        ax[1].invert_yaxis(); ax[1].grid(alpha=0.3, axis="x")
    else:
        ax[1].text(0.5, 0.5, "no flag set anywhere", ha="center", va="center")
    ax[1].set_title("what each flag covers")
    fig.suptitle(cfg.name, y=1.02)
    return savefig(cfg, fig, "07_quality.png")


# --------------------------------------------------------------------------- #
# the run                                                                      #
# --------------------------------------------------------------------------- #

def run(cfg, argv=None):
    args = parse_args(cfg, argv)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    os.environ.setdefault("HYPERPROC_CACHE_DIR", str(cfg.out / "cache"))

    t_start = time.time()
    import hyperproc as hp
    import matplotlib
    matplotlib.use("Agg")

    cfg.out.mkdir(parents=True, exist_ok=True)
    cfg.figs.mkdir(parents=True, exist_ok=True)

    print(f"hyperproc {hp.__version__}  |  python {sys.version.split()[0]}")
    print(f"sensor  {cfg.name}")
    print(f"window  {args.window or 'whole scene'}")
    print(f"data    {cfg.data}")
    print(f"out     {cfg.out}")
    if cfg.note:
        print(f"note    {cfg.note}")

    summary = {"sensor": cfg.name, "hyperproc": hp.__version__,
               "started": datetime.now().isoformat(timespec="seconds"),
               "window": args.window, "format": args.format,
               "sza_ref": args.sza_ref, "vza_ref": args.vza_ref,
               "diag_nm": args.diag_nm}

    l1_path, l2_path = acquire(cfg, args, hp)
    cfg._l1_path = l1_path
    summary["granules"] = {"l1": l1_path.name, "l2": l2_path.name}
    if args.stage == "data":
        return finish(cfg, summary, t_start)

    l1, l2, l1_sub, l2_sub, written, content = read_and_export(
        cfg, args, hp, l1_path, l2_path)
    summary["exports"] = written
    summary["window_content"] = content
    if not args.no_figures:
        figure_inputs(cfg, hp, l1_sub, l2_sub, args.diag_nm)
        figure_geometry(cfg, l1_sub)
    if args.stage == "read":
        return finish(cfg, summary, t_start)

    ac = run_ac(cfg, args, hp, l1_path)
    summary["ac"] = {"reflectance": str(ac["reflectance"])} if ac else None
    if ac and not args.no_figures:
        # The product is on a map grid whatever the input was, so a swath L2
        # has to be projected before the two can be matched by coordinate. The
        # window's projection lands on the same grid the retrieval produced.
        ref = l2 if l2.attrs.get("crs") else for_export(hp, l2_sub)
        summary["ac_vs_provider"] = figure_ac_vs_provider(cfg, ac, ref, args.diag_nm)
    if args.stage == "ac":
        return finish(cfg, summary, t_start)

    step("MODIS BRDF parameters")
    params = fetch_modis(cfg, hp, l2_sub)
    acb = l2_brdf = None
    if params is not None:
        if ac is not None:
            acb = run_ac_brdf(cfg, args, hp, l1_path, params)
            summary["ac_brdf"] = {"reflectance": str(acb["reflectance"])}
        l2_brdf, path = run_l2_brdf(cfg, args, hp, l2_sub, params)
        summary["l2_brdf"] = {"product": str(path)}
        step("did the BRDF step do what it should?")
        summary["brdf_verdict"] = judge_brdf(l2_sub, l2_brdf, params, args.diag_nm)

    q, shares = quality(hp, l2_sub)
    summary["quality_shares"] = shares

    if not args.no_figures:
        step("figures")
        if l2_brdf is not None:
            summary["l2_brdf_change_pct"] = figure_brdf(
                cfg, l2_sub, l2_brdf, "provider L2 -> BRDF",
                "05_brdf_l2.png", args.diag_nm)
        if ac is not None and acb is not None:
            summary["ac_brdf_change_pct"] = figure_brdf(
                cfg, read_product(ac["reflectance"], sensor=cfg.name),
                read_product(acb["reflectance"], sensor=cfg.name),
                "hyperproc AC -> BRDF", "06_brdf_ac.png", args.diag_nm)
        figure_quality(cfg, q, shares)
        figure_spectra(cfg, hp, ac, acb, l2_sub, l2_brdf, args.diag_nm)

    return finish(cfg, summary, t_start)


def finish(cfg, summary, t_start):
    summary["minutes"] = round((time.time() - t_start) / 60, 2)
    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    path = cfg.out / "summary.json"
    path.write_text(json.dumps(summary, indent=2, default=str))
    step("done")
    say(f"{summary['minutes']:.1f} minutes")
    say(f"products {cfg.out}")
    figs = sorted(cfg.figs.glob("*.png"))
    say(f"figures  {len(figs)}")
    for f in figs:
        say(f"  {f.name}")
    say(f"summary  {path}")
    return 0
