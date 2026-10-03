"""Run ISOFIT's ``apply_oe`` on a hyperproc L1B dataset and read the result back.

The route is the one JPL runs operationally for EMIT, AVIRIS-3 and AVIRIS-5:
``isofit apply_oe`` with the sRTMnet emulator, a water-vapour presolve, SLIC
superpixels and the analytical-line extrapolation to every pixel. Nothing is
reimplemented here; this module writes the inputs (:mod:`hyperproc.atmos.inputs`),
chooses the few parameters that depend on the scene, launches the ISOFIT
command in a subprocess, and turns ``output/<fid>_rfl`` and friends into a
hyperproc dataset with ``level = "L2A"`` and ``stem = <stem>_ac``.

What is decided automatically, and how
--------------------------------------
* **Look-up-table axes**: ``apply_oe`` reads the spans of view zenith, sun
  zenith and relative azimuth from the obs file and adds an axis only where a
  span exceeds its threshold; elevation and water vapour come from the loc
  file and the presolve. Nothing to set.
* **Atmosphere profile** (``atmosphere="auto"``): :func:`atmosphere_for` picks
  the MODTRAN/6S class from the mean latitude and the month. The winter
  classes cap the retrievable water vapour hard (MIDLAT_WINTER at 1.37 g/cm²
  at sea level), so winter is only chosen in the core winter months
  (Nov-Feb north, May-Aug south); pass a class name to override.
* **Aerosol model**: sRTMnet is trained on one continental aerosol, so only
  ``"continental"`` is valid on it. ``engine="6s"`` and ``engine="LibRadTran"``
  keep the whole ``apply_oe`` orchestration and only change the engine that
  fills the look-up table (through :mod:`hyperproc.atmos._runner`), so they
  accept the models in :data:`hyperproc.atmos.aerosols.AEROSOLS` and cost about
  the same as sRTMnet for the same scene.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import xarray as xr

from hyperproc._ncrc import rc_warning, unterminated_rc_files
from hyperproc.atmos.aerosols import AEROSOLS
from hyperproc.atmos.inputs import FILL, Inputs, prepare_inputs

ENGINES = ("sRTMnet", "6s", "LibRadTran")
ATMOSPHERES = ("ATM_TROPICAL", "ATM_MIDLAT_SUMMER", "ATM_MIDLAT_WINTER",
               "ATM_SUBARC_SUMMER", "ATM_SUBARC_WINTER")
#: JPL's operational EMIT surface prior (emit-main ops config, V2 pipeline of
#: 2026): five spectral libraries with per-window regularisation. Older recipes
#: in the same asset directory: surface_20221020.json (used for the V001
#: products), surface_20240103.json.
DEFAULT_SURFACE = "surface_20260113.json"
LINES = ("analytical", "empirical", "pixel")


# --- scene-dependent choices --------------------------------------------------

def atmosphere_for(lat: float, month: int) -> str:
    """MODTRAN atmosphere class for a scene at ``lat`` degrees in ``month``.

    Tropical below 23.5 degrees, mid-latitude below 60, sub-arctic above.
    Summer variants are the default; the winter variant is used only for
    Nov-Feb in the north and May-Aug in the south, because ISOFIT derives the
    upper bound of the water-vapour grid from the class (summer 5.35 g/cm²,
    winter 1.37 at sea level) and a humid scene under a winter class rails.
    """
    a = abs(float(lat))
    winter = int(month) in ((5, 6, 7, 8) if lat < 0 else (11, 12, 1, 2))
    if a < 23.5:
        return "ATM_TROPICAL"
    if a < 60.0:
        return "ATM_MIDLAT_WINTER" if winter else "ATM_MIDLAT_SUMMER"
    return "ATM_SUBARC_WINTER" if winter else "ATM_SUBARC_SUMMER"


def _env():
    try:
        from isofit.data import env
    except ImportError as exc:
        raise ImportError("ISOFIT is not installed: pip install 'hyperproc[atmos]'") from exc
    return env


def emulator_path() -> Path:
    """The sRTMnet weights file under ISOFIT's asset base."""
    d = Path(_env().srtmnet)
    files = sorted(p for p in d.glob("sRTMnet_v*.h5") if "aux" not in p.name)
    if not files:
        raise FileNotFoundError(f"no sRTMnet_v*.h5 under {d}; run hyperproc-atmos-setup")
    return files[-1]


def surface_recipe(name: str | Path = DEFAULT_SURFACE) -> Path:
    """A surface-prior recipe (``.json``) or built model (``.mat``).

    A bare name is looked up in ISOFIT's ``surface`` asset directory.
    """
    p = Path(name).expanduser()
    if p.is_file():
        return p.resolve()
    cand = Path(_env().surface) / str(name)
    if cand.is_file():
        return cand.resolve()
    raise FileNotFoundError(f"surface prior {name!r} not found (looked in {Path(_env().surface)})")


def _cache_dir() -> Path:
    return Path(os.environ.get("HYPERPROC_CACHE_DIR", "~/.cache/hyperproc")).expanduser() / "surface"


def _surface_key(recipe: Path, inputs: Inputs) -> str:
    chn, wl, fwhm = np.loadtxt(inputs.wavelengths).T
    h = hashlib.sha1(np.round(wl, 3).tobytes() + np.round(fwhm, 3).tobytes()).hexdigest()[:10]
    return f"{recipe.stem}_{inputs.sensor}_{len(wl)}b_{h}.mat"


def resolve_surface(inputs: Inputs, surface=None, cache: bool = True) -> tuple[Path, Path | None]:
    """``(surface_path_to_pass, cached_mat_to_fill)``.

    Building the five-library prior takes a couple of minutes and depends only
    on the wavelength grid, so the built ``.mat`` is cached per sensor and
    grid under ``~/.cache/hyperproc/surface`` (``HYPERPROC_CACHE_DIR`` to move
    it). When the cache has it, the ``.mat`` is passed and nothing is rebuilt.
    """
    recipe = surface_recipe(surface or DEFAULT_SURFACE)
    if recipe.suffix == ".mat" or not cache:
        return recipe, None
    cached = _cache_dir() / _surface_key(recipe, inputs)
    if cached.is_file():
        return cached, None
    return recipe, cached


# --- the command ----------------------------------------------------------------

def build_command(inputs: Inputs, engine: str = "sRTMnet", workers: int = 24, atmosphere: str = "auto",
                  aerosol_model: str = "continental", segmentation_size: int = 40, line: str = "analytical",
                  presolve: bool = True, surface=None, num_neighbors=None, terrain_style: str = "flat",
                  pressure_elevation: bool = False, emulator: str | Path | None = None,
                  ozone: float | None = None, band_model: str = "coarse", inversion_windows=None,
                  aot_prior_sigma: float | None = None, config_overrides: dict | None = None,
                  ray_temp_dir: str | None = None, log_level: str = "INFO", extra=()) -> list[str]:
    """The ``isofit apply_oe`` command line for ``inputs``.

    Args:
        engine: ``"sRTMnet"`` (JPL's operational emulator), ``"6s"`` or
            ``"LibRadTran"``. The last two run the same ``apply_oe`` pipeline
            with the table engine swapped by :mod:`hyperproc.atmos._runner`.
        workers: Ray CPUs for the look-up table and the inversions.
        atmosphere: ``"auto"`` (:func:`atmosphere_for`) or one of :data:`ATMOSPHERES`.
            6S ignores it (its template uses user-defined H2O/O3 on a standard
            profile); libRadtran maps it to the matching AFGL profile.
        aerosol_model: ``"continental"`` only on sRTMnet; see
            :data:`hyperproc.atmos.aerosols.AEROSOLS` for 6S and libRadtran.
        ozone: ozone column in atm-cm for 6S and libRadtran (default ISOFIT's 0.30).
        band_model: libRadtran REPTRAN resolution, ``"coarse"`` (default), ``"medium"`` or ``"fine"``.
        inversion_windows: fit windows in nm as ``((lo, hi), ...)``; default the
            sensor's entry in :data:`hyperproc.atmos.inputs.SENSORS`, else
            ISOFIT's own per-sensor defaults.
        aot_prior_sigma: width of the aerosol prior. ISOFIT 4.1.5 uses 0.1
            around a prior mean of 0.138, which pulls the retrieval toward
            that value and is why our AOT sits below the providers'; JPL's
            version-1 EMIT products used a loose prior instead. A number here
            replaces it (1.0 is effectively unconstrained).
        config_overrides: any other ISOFIT config values, keyed by
            slash-separated path, e.g.
            ``{"forward_model/atmosphere/statevector/H2OSTR/prior_sigma": 100}``.
        segmentation_size: SLIC superpixel size in pixels (JPL: 40).
        line: ``"analytical"`` (JPL), ``"empirical"``, or ``"pixel"`` for a
            full optimal-estimation inversion of every pixel (slow).
        presolve: retrieve water vapour first and centre its grid on the scene.
        surface: recipe ``.json`` or built ``.mat``; default :data:`DEFAULT_SURFACE`.
        num_neighbors: how many superpixels the analytical line fits each
            atmospheric term over: a dict keyed by term, one number for all,
            or a sequence in the order of :func:`atm_terms`. The default is
            :data:`ATM_NEIGHBORS`, which keeps the structure of the retrieved
            fields; every value is capped by the scene's superpixel count.
        terrain_style: ``"flat"`` (default, JPL's EMIT setting) lights every
            pixel with cos(sun zenith); ``"dem"`` uses the per-pixel cos(i)
            from the obs file inside the forward model, which normalises the
            direct irradiance for slope and aspect during the retrieval.
            hyperproc corrects topography in its own stage (SCS+C), so
            ``"flat"`` keeps the two from being applied twice.
        pressure_elevation: add surface elevation to the state vector
            (JPL's V1 EMIT processing did; V2 does not).
        emulator: a specific sRTMnet weights file (``sRTMnet_v100.h5`` to
            emulate JPL's V1 products); default the newest under the asset base.
        extra: further raw ``apply_oe`` options appended verbatim.
    """
    if engine not in ENGINES:
        raise ValueError(f"engine must be one of {ENGINES}, got {engine!r}")
    if aerosol_model not in AEROSOLS[engine]:
        hint = ("sRTMnet is trained on one continental aerosol; use engine='6s' or 'LibRadTran' to vary it"
                if engine == "sRTMnet" else f"choose from {AEROSOLS[engine]}")
        raise ValueError(f"aerosol_model {aerosol_model!r} is not available on {engine}: {hint}")
    if band_model not in ("coarse", "medium", "fine"):
        raise ValueError("band_model must be 'coarse', 'medium' or 'fine'")
    if line not in LINES:
        raise ValueError(f"line must be one of {LINES}")
    if terrain_style not in ("flat", "dem"):
        raise ValueError("terrain_style must be 'flat' or 'dem'")
    if atmosphere == "auto":
        month = int(inputs.datetime[5:7])
        atmosphere = atmosphere_for(inputs.stats.get("lat_mean", 0.0), month)
    if atmosphere not in ATMOSPHERES:
        raise ValueError(f"atmosphere must be 'auto' or one of {ATMOSPHERES}")
    surface_path, _ = resolve_surface(inputs, surface)
    work = Path(inputs.work_dir)
    cmd = [sys.executable, "-m", "isofit", "apply_oe", inputs.rdn, inputs.loc, inputs.obs, str(work), inputs.code,
           "--surface_path", str(surface_path),
           "--emulator_base", str(Path(emulator).expanduser().resolve() if emulator else emulator_path()),
           "--n_cores", str(int(workers)),
           "--atmosphere_type", atmosphere,
           "--segmentation_size", str(int(segmentation_size)),
           "--terrain_style", terrain_style,
           "--log_file", str(work / "isofit.log"),
           "--logging_level", log_level]
    if presolve:
        cmd.append("--presolve")
    if line == "analytical":
        cmd.append("--analytical_line")
    elif line == "empirical":
        cmd.append("--empirical_line")
    if line != "pixel":
        counts = resolve_neighbors(inputs, segmentation_size, num_neighbors)
        # the empirical line takes a single count for the whole state
        for n in (counts if line == "analytical" else counts[:1]):
            cmd += ["--num_neighbors", str(int(n))]
    if pressure_elevation:
        cmd.append("--pressure_elevation")
    from hyperproc.atmos.inputs import SENSORS
    windows = inversion_windows if inversion_windows is not None else SENSORS[inputs.sensor].inversion_windows
    for lo, hi in (windows or ()):
        cmd += ["--inversion_windows", f"{float(lo):g}", f"{float(hi):g}"]
    if ray_temp_dir:
        cmd += ["--ray_temp_dir", str(ray_temp_dir)]
    cmd += [str(e) for e in extra]
    overrides = dict(config_overrides or {})
    if aot_prior_sigma is not None:
        overrides["forward_model/atmosphere/statevector/AOT550/prior_sigma"] = float(aot_prior_sigma)
    if engine != "sRTMnet" or overrides:
        head = [sys.executable, "-m", "hyperproc.atmos._runner"]
        if engine != "sRTMnet":
            head += ["--engine", engine, "--aerosol-model", aerosol_model]
            if ozone is not None:
                head += ["--ozone", f"{float(ozone):g}"]
            if engine == "LibRadTran":
                head += ["--band-model", band_model]
        for path, value in overrides.items():
            head += ["--set", f"{path}={json.dumps(value)}"]
        cmd = head + ["--"] + cmd[4:]          # drop "python -m isofit apply_oe"; the runner calls it
    return cmd


#: Superpixel neighbours the analytical line fits each atmospheric term over.
#: ISOFIT uses one count for every term (400 at ``segmentation_size`` 40),
#: which fits a plane through some 4 km of scene and flattens the retrieved
#: fields: on the EMIT test granule our aerosol map came out 8.7 times
#: smoother from pixel to pixel than JPL's. JPL's own production gives each
#: term its own count instead, because aerosol varies over kilometres while
#: water vapour does not. These are the defaults here; pass ``num_neighbors``
#: to override, as a dict per term, one number for all, or a sequence in the
#: order of :func:`atm_terms`.
ATM_NEIGHBORS = {"AOT550": 100, "H2OSTR": 10, "CO2": 200, "surface_elevation_km": 200}


def atm_terms(inputs: Inputs) -> list:
    """Atmospheric terms the analytical line interpolates, in ISOFIT's order.

    Taken from a previous run's products where there is one (the interpolated
    atmosphere file names its bands), otherwise the two terms every retrieval
    has. Instrument terms in the state vector (EMIT's EOFs) are not
    interpolated and are left out.
    """
    for prod in ("atm_interp", "subs_state"):
        path = inputs.output(prod)
        if path.is_file():
            names = _hdr_list(_hdr(path), "band names") or []
            terms = [n for n in names if n in ATM_NEIGHBORS]
            if terms:
                return terms
    return ["AOT550", "H2OSTR"]


def segment_count(inputs: Inputs) -> int | None:
    """How many superpixels a previous run of this work dir actually produced.

    ISOFIT's SLIC segmentation writes ``output/<fid>_lbl``; label 0 is the
    no-data class, so the count is the maximum label. None when the file is
    not there yet.
    """
    lbl = inputs.output("lbl")
    if not lbl.is_file():
        return None
    try:
        import numpy as np

        hdr = _hdr(lbl)
        n = int(hdr["lines"]) * int(hdr["samples"])
        arr = np.fromfile(lbl, dtype="<f4", count=n)
        return int(np.nanmax(arr))
    except (OSError, KeyError, ValueError):
        return None


def neighbor_cap(inputs: Inputs, segmentation_size: int) -> int:
    """Most neighbours the scene can support.

    Asking for more neighbours than there are superpixels makes the KD-tree
    query return out-of-range indices and the analytical line crashes with an
    IndexError. The count is estimated conservatively at half the nominal
    count, and a previous run's label image, where there is one, can only
    lower that (SLIC merges small segments, so it yields fewer than
    pixels/size: a 60 x 60 patch at size 40 gave 61, not 90).

    Only lower: taking the measured count outright made the cap - and with it
    ``--num_neighbors`` - depend on whether the work dir had run before. On a
    window small enough for the cap to bind, the second call then always
    asked for different settings from the first and found its own finished
    product "made with different settings" (45 against 72 on 60 x 60 DESIS
    and EnMAP windows). After a crash the measured count is still what lowers
    the retry.
    """
    ny, nx, _ = inputs.shape
    valid = float(inputs.stats.get("valid_fraction", 1.0)) or 1.0
    estimate = max(5, int(0.5 * valid * ny * nx / max(1, segmentation_size)))
    measured = segment_count(inputs)
    if measured:
        return min(estimate, max(5, int(0.8 * measured)))
    return estimate


def resolve_neighbors(inputs: Inputs, segmentation_size: int, num_neighbors=None) -> list:
    """Neighbour count per atmospheric term, in the order the analytical line wants.

    ``num_neighbors`` may be a dict keyed by term, a single number for every
    term, or a sequence matching :func:`atm_terms`; None uses
    :data:`ATM_NEIGHBORS`. Every value is capped by :func:`neighbor_cap`.
    """
    terms = atm_terms(inputs)
    if num_neighbors is None:
        want = [ATM_NEIGHBORS.get(t, 100) for t in terms]
    elif isinstance(num_neighbors, dict):
        want = [int(num_neighbors.get(t, ATM_NEIGHBORS.get(t, 100))) for t in terms]
    elif isinstance(num_neighbors, (int, float)):
        want = [int(num_neighbors)] * len(terms)
    else:
        want = [int(v) for v in num_neighbors]
        if len(want) != len(terms):
            raise ValueError(f"num_neighbors has {len(want)} values but this retrieval interpolates {terms}")
    cap = neighbor_cap(inputs, segmentation_size)
    return [max(5, min(w, cap)) for w in want]


def _clean_partial(inputs: Inputs) -> None:
    """Remove what an interrupted or failed run left half-written.

    ISOFIT creates its output files before filling them and, on resume,
    trusts any file that exists (a presolve file from a run that died in the
    engine constructor was taken as "existing h2o-presolve solutions"). So
    everything under ``output/`` goes, together with the assembled
    ``lut.zarr`` stores. The raw radiative-transfer simulations beside them
    (6S ``LUT_*`` files, libRadtran ``*.out``), which are the expensive part,
    stay: every engine skips simulations whose files already exist.
    """
    work = Path(inputs.work_dir)
    out = work / "output"
    if out.is_dir():
        for p in out.iterdir():
            if p.is_file():
                p.unlink()
    for lut in ("lut_h2o", "lut_full"):
        z = work / lut / "lut.zarr"
        if z.is_dir():
            shutil.rmtree(z, ignore_errors=True)
        # a simulation that crashed leaves an empty output; the engines skip
        # points whose output exists, so an empty one would poison the table
        for sim in (work / lut).glob("*.out") if (work / lut).is_dir() else ():
            if sim.stat().st_size == 0:
                sim.unlink()


def run_record(inputs: Inputs) -> dict | None:
    """The ``hyperproc_ac.json`` of the work dir, or None."""
    rec = Path(inputs.work_dir) / "hyperproc_ac.json"
    if not rec.is_file():
        return None
    try:
        return json.loads(rec.read_text())
    except ValueError:
        return None


_SETTING_FLAGS = ("--engine", "--aerosol-model", "--ozone", "--band-model", "--set", "--surface_path",
                  "--emulator_base", "--atmosphere_type", "--terrain_style", "--segmentation_size", "--num_neighbors")
_SETTING_SWITCHES = ("--presolve", "--analytical_line", "--empirical_line", "--pressure_elevation", "--retrieve_co2")


def settings_of(command: list[str]) -> dict:
    """The retrieval-relevant options of an ``apply_oe`` command (not cores or logs)."""
    import re
    out = {}
    for flag in _SETTING_FLAGS:
        if flag in command:
            val = command[command.index(flag) + 1]
            if flag == "--surface_path":
                # a cached build "<recipe>_<sensor>_<n>b_<hash>.mat" counts as its recipe
                val = re.sub(r"_[A-Za-z0-9-]+_\d+b_[0-9a-f]{10}$", "", Path(val).stem)
            elif flag == "--emulator_base":
                val = Path(val).name
            out[flag] = val
    for sw in _SETTING_SWITCHES:
        out[sw] = sw in command
    out.setdefault("--engine", "sRTMnet")
    out.setdefault("--aerosol-model", "continental")
    if "--set" in command:
        out["--set"] = tuple(command[i + 1] for i, a in enumerate(command) if a == "--set")
    if "--inversion_windows" in command:
        idx = [i for i, a in enumerate(command) if a == "--inversion_windows"]
        out["--inversion_windows"] = tuple((command[i + 1], command[i + 2]) for i in idx)
    return out


def is_complete(inputs: Inputs) -> bool:
    """True when a reflectance product exists and no run record contradicts it."""
    if not inputs.output("rfl").is_file():
        return False
    rec = run_record(inputs)
    return rec is None or rec.get("returncode") == 0


def _tail(path: Path, n: int = 30) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n:])


def run_isofit(inputs: Inputs, command: list[str], timeout: float | None = None, verbose: bool = True) -> dict:
    """Run ``command`` (from :func:`build_command`), blocking, with logs in the work dir.

    Returns a record (command, start, end, seconds, returncode, isofit version)
    that is also written to ``<work_dir>/hyperproc_ac.json``. Raises
    RuntimeError with the tail of the log when ISOFIT exits non-zero or
    leaves no reflectance file.
    """
    work = Path(inputs.work_dir)
    out_txt = work / "apply_oe.stdout.txt"
    t0 = time.time()
    if not is_complete(inputs):
        _clean_partial(inputs)
    rec = {"command": command, "start": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
           "seconds": None, "returncode": None}
    (work / "hyperproc_ac.json").write_text(json.dumps(rec, indent=2))
    if verbose:
        print("running:", " ".join(command[:5]), "...", flush=True)
        print(f"  log: {work / 'isofit.log'}   stdout: {out_txt}", flush=True)
    # One BLAS thread per Ray worker: with the default (all cores) every one of
    # the n_cores workers spawns a full thread pool and they fight for the CPU.
    env = dict(os.environ)
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        env.setdefault(var, "1")
    # Every Ray worker imports netCDF4, and netCDF-C reads the rc files at
    # import. One of them ending without a newline is enough to crash workers
    # at random, so say so before a retrieval that takes minutes, not after.
    if "NCRCENV_RC" not in env:
        bad = unterminated_rc_files(Path.home(), work)
        if bad:
            warnings.warn(rc_warning(bad), RuntimeWarning, stacklevel=2)
    with open(out_txt, "w") as fh:
        proc = subprocess.run(command, stdout=fh, stderr=subprocess.STDOUT, cwd=str(work), timeout=timeout, env=env)
    rec.update(seconds=round(time.time() - t0, 1), returncode=proc.returncode)
    try:
        import isofit
        rec["isofit_version"] = isofit.__version__
    except Exception:
        pass
    (work / "hyperproc_ac.json").write_text(json.dumps(rec, indent=2))
    rfl = inputs.output("rfl")
    if proc.returncode != 0 or not rfl.is_file():
        raise RuntimeError(f"apply_oe failed (exit {proc.returncode}) after {rec['seconds']} s; "
                           f"last lines of {out_txt}:\n{_tail(out_txt)}\n--- isofit.log:\n{_tail(work / 'isofit.log')}")
    if verbose:
        print(f"apply_oe finished in {rec['seconds'] / 60:.1f} min -> {rfl}", flush=True)
    return rec


# --- reading the products back --------------------------------------------------

def _hdr(path: Path) -> dict:
    from hyperproc.atmos.inputs import hdr_path
    from hyperproc.readers.aviris import read_hdr
    hdr = hdr_path(path)
    return read_hdr(hdr if hdr.is_file() else path.with_suffix(".hdr"))


def _hdr_list(hdr: dict, key: str) -> list[str] | None:
    if key not in hdr:
        return None
    return [v.strip() for v in hdr[key].split(",") if v.strip()]


def _open_bil(path: Path, chunks_rows: int | None = None) -> xr.DataArray:
    """Lazy ``(band, y, x)`` view of an ENVI file, FILL -> NaN, float32."""
    import rioxarray
    hdr = _hdr(path)
    nx, nb = int(hdr.get("samples", 0) or 0), int(hdr.get("bands", 0) or 0)
    rows = chunks_rows or int(np.clip(64 * 2**20 // max(1, nx * nb * 4), 1, 2048))
    da = rioxarray.open_rasterio(str(path), chunks={"band": -1, "y": rows, "x": -1}, masked=False)
    da = da.astype("float32")
    return da.where(da != np.float32(FILL))


def read_outputs(source: Inputs | str | Path, template: xr.Dataset | None = None,
                 uncertainty: bool = True) -> xr.Dataset:
    """The ISOFIT products as a hyperproc dataset.

    Args:
        source: the :class:`Inputs` of the run, or its work directory.
        template: the L1B dataset the inputs were written from (already cut
            to the same window). Its coordinates, 2-D layers and attributes
            are carried over so the result is a drop-in for the correction
            and export steps. Without it the result has bare indices.
        uncertainty: also attach the posterior reflectance uncertainty cube.

    Returns:
        ``reflectance (y, x, wavelength)`` lazy float32, plus ``aot550`` and
        ``h2o`` (per pixel, from ``_atm_interp`` on the analytical/empirical
        routes or from ``_state`` on the per-pixel route), ``segment`` where a
        superpixel label image exists, and ``uncertainty`` when asked.
    """
    inputs = source if isinstance(source, Inputs) else Inputs.load(source)
    rfl_path = inputs.output("rfl")
    if not rfl_path.is_file():
        raise FileNotFoundError(f"no reflectance product at {rfl_path}; run correct() first")
    if not is_complete(inputs):
        raise RuntimeError(f"{rfl_path} belongs to a run that did not finish (see hyperproc_ac.json); rerun correct()")
    hdr = _hdr(rfl_path)
    rfl = _open_bil(rfl_path)                        # (band, y, x)
    nb, ny, nx = rfl.shape
    wl = np.array([float(v) for v in hdr["wavelength"].split(",")]) if "wavelength" in hdr else np.arange(nb, dtype=float)
    fwhm = np.array([float(v) for v in hdr["fwhm"].split(",")]) if "fwhm" in hdr else None

    coords = {}
    if template is not None:
        if inputs.bands is not None and template.sizes["wavelength"] != nb:
            template = template.isel(wavelength=inputs.bands)
        if (template.sizes["y"], template.sizes["x"], template.sizes["wavelength"]) != (ny, nx, nb):
            raise ValueError(f"template {dict(template.sizes)} does not match the product {(ny, nx, nb)}; "
                             "pass the same window that produced the inputs")
        for c in ("wavelength", "fwhm", "good_wavelength", "band_index"):
            if c in template.coords:
                coords[c] = template[c]
        for c in ("x", "y"):
            if c in template.coords:
                coords[c] = template[c]
    coords.setdefault("wavelength", ("wavelength", wl))
    if fwhm is not None and "fwhm" not in coords:
        coords["fwhm"] = ("wavelength", fwhm)

    ds = xr.Dataset(coords=coords)
    ds["reflectance"] = (("y", "x", "wavelength"), rfl.transpose("y", "x", "band").data)
    ds["reflectance"].attrs.update(units="unitless", long_name="surface reflectance (ISOFIT)")
    if uncertainty and inputs.output("uncert").is_file():
        unc = _open_bil(inputs.output("uncert"))
        if unc.shape[0] >= nb:   # the uncertainty cube also carries the atmospheric state terms
            ds["uncertainty"] = (("y", "x", "wavelength"), unc.isel(band=slice(0, nb)).transpose("y", "x", "band").data)
            ds["uncertainty"].attrs.update(units="unitless", long_name="posterior reflectance uncertainty (1 sigma)")
    atm_path = next((p for p in (inputs.output("atm_interp"), inputs.output("state")) if p.is_file()), None)
    if atm_path is not None:
        names = _hdr_list(_hdr(atm_path), "band names") or []
        atm = _open_bil(atm_path)
        for band, name in enumerate(names):
            if name == "AOT550":
                ds["aot550"] = (("y", "x"), atm.isel(band=band).data)
                ds["aot550"].attrs.update(long_name="aerosol optical thickness at 550 nm", source=atm_path.name)
            elif name == "H2OSTR":
                ds["h2o"] = (("y", "x"), atm.isel(band=band).data)
                ds["h2o"].attrs.update(units="g/cm2", long_name="column water vapour", source=atm_path.name)
    lbl = inputs.output("lbl")
    if lbl.is_file():
        seg = _open_bil(lbl).isel(band=0)
        ds["segment"] = (("y", "x"), seg.data)
        ds["segment"].attrs.update(long_name="SLIC superpixel label")
    if template is not None:
        for name, var in template.data_vars.items():
            if var.ndim == 2 and var.dims == ("y", "x") and name not in ds:
                ds[name] = var
        ds.attrs.update(template.attrs)
    ds.attrs.update(level="L2A", product="RFL", units="unitless",
                    stem=(str(ds.attrs.get("stem") or inputs.stem or inputs.fid)) + "_ac",
                    ac_engine="sRTMnet", ac_aerosol_model="continental", ac_fid=inputs.fid, ac_work_dir=inputs.work_dir,
                    ac_reflectance_file=str(rfl_path), fill_value=str(FILL))
    rec = Path(inputs.work_dir) / "hyperproc_ac.json"
    if rec.is_file():
        try:
            r = json.loads(rec.read_text())
            ds.attrs["ac_command"] = " ".join(r.get("command", []))
            ds.attrs["ac_isofit_version"] = str(r.get("isofit_version", ""))
            ds.attrs["ac_seconds"] = r.get("seconds", "")
            cmd = r.get("command", [])
            if "--atmosphere_type" in cmd:
                ds.attrs["ac_atmosphere"] = cmd[cmd.index("--atmosphere_type") + 1]
            if "--terrain_style" in cmd:
                ds.attrs["ac_terrain_style"] = cmd[cmd.index("--terrain_style") + 1]
            if "--emulator_base" in cmd:
                ds.attrs["ac_emulator"] = Path(cmd[cmd.index("--emulator_base") + 1]).name
            for flag, key in (("--engine", "ac_engine"), ("--aerosol-model", "ac_aerosol_model"),
                              ("--ozone", "ac_ozone_atm_cm"), ("--band-model", "ac_band_model")):
                if flag in cmd:
                    ds.attrs[key] = cmd[cmd.index(flag) + 1]
            if ds.attrs["ac_engine"] != "sRTMnet":
                ds.attrs.pop("ac_emulator", None)
        except (OSError, ValueError):
            pass
    return ds


# --- the entry point ------------------------------------------------------------

def redo_line(inputs: Inputs, verbose: bool = True) -> None:
    """Drop only what the analytical line produced, keeping the retrieval.

    The look-up tables, the segmentation and the superpixel inversions are the
    expensive part and do not depend on how the atmospheric state is
    interpolated, so tuning ``num_neighbors`` costs only the last stage
    (27 of 51 minutes on the EMIT test granule).
    """
    for prod in ("rfl", "uncert", "atm_interp"):
        for p in (inputs.output(prod), inputs.output(prod).with_name(inputs.output(prod).name + ".hdr")):
            if p.is_file():
                p.unlink()
    rec = Path(inputs.work_dir) / "hyperproc_ac.json"
    if rec.is_file():
        rec.unlink()
    if verbose:
        print("redo='line': reflectance, uncertainty and interpolated atmosphere removed; "
              "look-up tables and superpixel retrieval kept", flush=True)


def correct(ds: xr.Dataset, work_dir: str | Path, engine: str = "sRTMnet", workers: int = 24,
            atmosphere: str = "auto", aerosol_model: str = "continental", segmentation_size: int = 40,
            line: str = "analytical", presolve: bool = True, surface=None, window=None,
            overwrite: bool = False, redo: str | None = None, dry_run: bool = False,
            timeout: float | None = None, verbose: bool = True, **kwargs) -> xr.Dataset | dict:
    """Atmospherically correct an L1B radiance dataset with ISOFIT.

    Writes the inputs under ``work_dir/input``, runs ``apply_oe`` (see
    :func:`build_command` for every parameter), and returns the products
    through :func:`read_outputs` with ``ds`` as the template.

    ``work_dir`` is resumable the way ISOFIT is: an existing look-up table,
    presolve or reflectance file is reused, so a second call on the same
    directory returns in seconds. ``overwrite=True`` clears ISOFIT's
    ``config``, ``lut_*`` and ``output`` directories first (the inputs are
    rewritten only when their size no longer matches).

    ``redo="line"`` keeps the look-up tables and the superpixel retrieval and
    redoes only the analytical line, which is what a change of
    ``num_neighbors`` needs; ``redo="all"`` is the same as ``overwrite``.

    ``dry_run=True`` writes the inputs and returns ``{"inputs", "command"}``
    without launching ISOFIT.
    """
    inputs = prepare_inputs(ds, work_dir, window=window, overwrite=False, verbose=verbose)
    work = Path(inputs.work_dir)
    if redo not in (None, "line", "all"):
        raise ValueError("redo must be None, 'line' or 'all'")
    if overwrite or redo == "all":
        for sub in ("config", "lut_full", "lut_h2o", "output", "data"):
            shutil.rmtree(work / sub, ignore_errors=True)
        overwrite = True
    elif redo == "line":
        redo_line(inputs, verbose)
    surface_path, cache_target = resolve_surface(inputs, surface, cache=kwargs.pop("surface_cache", True))
    cmd = build_command(inputs, engine=engine, workers=workers, atmosphere=atmosphere, aerosol_model=aerosol_model,
                        segmentation_size=segmentation_size, line=line, presolve=presolve, surface=surface_path,
                        **kwargs)
    if dry_run:
        if verbose:
            print(" \\\n    ".join(cmd))
        return {"inputs": inputs, "command": cmd}
    if is_complete(inputs) and not overwrite:
        rec = run_record(inputs) or {}
        before, now = settings_of(rec.get("command", [])), settings_of(cmd)
        changed = {k: (before.get(k), now[k]) for k in now if before.get(k) != now[k]} if rec.get("command") else {}
        if changed:
            warnings.warn(f"{work} holds a finished product made with different settings "
                          f"{changed} (old, new); returning it unchanged. Pass overwrite=True to redo "
                          "the retrieval with the new settings.", stacklevel=2)
        elif verbose:
            print(f"reflectance product already present: {inputs.output('rfl')} (overwrite=True to redo)")
    else:
        try:
            run_isofit(inputs, cmd, timeout=timeout, verbose=verbose)
        except RuntimeError as exc:
            # The analytical line asked for more neighbours than the scene has
            # superpixels. Segmentation has run by now, so the label image
            # gives the real count; rebuild the command and try once more.
            retry = ("IndexError" in str(exc) and "--num_neighbors" not in kwargs
                     and segment_count(inputs) and resolve_neighbors(inputs, segmentation_size, kwargs.get('num_neighbors')) != 
                     [n for i, n in enumerate(cmd) if i and cmd[i - 1] == "--num_neighbors"])
            if not retry:
                raise
            cmd = build_command(inputs, engine=engine, workers=workers, atmosphere=atmosphere,
                                aerosol_model=aerosol_model, segmentation_size=segmentation_size,
                                line=line, presolve=presolve, surface=surface_path, **kwargs)
            if verbose:
                print(f"retrying with {resolve_neighbors(inputs, segmentation_size, kwargs.get('num_neighbors'))} neighbours "
                      f"({segment_count(inputs)} superpixels measured)", flush=True)
            run_isofit(inputs, cmd, timeout=timeout, verbose=verbose)
        built = work / "data" / "surface.mat"
        if cache_target is not None and built.is_file() and not cache_target.is_file():
            cache_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built, cache_target)
            if verbose:
                print(f"surface model cached -> {cache_target}")
    tmpl, _ = _window(ds, window)
    return read_outputs(inputs, template=tmpl)


def _window(ds, window):
    from hyperproc.atmos.inputs import _apply_window
    return _apply_window(ds, window)
