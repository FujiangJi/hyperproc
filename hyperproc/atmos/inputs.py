"""Turn a hyperproc L1B dataset into the three ENVI files ISOFIT reads.

``isofit apply_oe`` wants, for one scene:

``<fid>_rdn``
    at-sensor radiance in µW cm⁻² nm⁻¹ sr⁻¹, band-interleaved-by-line float32,
    with ``wavelength`` and ``fwhm`` (nm) in the header;
``<fid>_loc``
    three float64 bands: longitude, latitude (WGS-84 degrees), elevation (m);
``<fid>_obs``
    eleven float64 bands in JPL's order: path length (m), to-sensor azimuth
    and zenith, to-sun azimuth and zenith (degrees), solar phase, slope,
    aspect, cos(i), UTC time (decimal hours), Earth-sun distance (AU).

The file id ``fid`` is not free: ``apply_oe`` slices it from the radiance
file name and parses the acquisition time out of it with a per-sensor
pattern, so :data:`SENSORS` carries that pattern for every hyperproc sensor
together with the radiance unit factor and the ``apply_oe`` sensor code.

Every hyperproc reader already exposes the ingredients as dataset layers
(``sza, saa, vza, vaa, slope, aspect, cos_i, elev, lat, lon`` and, for the
JPL products, ``path_length, utc_time, solar_phase``), so the writer here is
mostly bookkeeping: unit scaling, NaN to -9999, and streaming the cube out in
row blocks so a full granule never sits in memory.
"""
from __future__ import annotations

import json
import re
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

from hyperproc.io import main_var

#: ISOFIT's no-data value, used in every file written here.
FILL = -9999.0

#: Wavelengths the radiative transfer can produce (nm). 6S simulates
#: 350-2500 nm and the sRTMnet emulator is trained on that same grid, so a
#: band outside it has no atmosphere to invert: ISOFIT builds the look-up
#: table on the bands it can simulate and then fails when the two band counts
#: disagree (PACE OCI's 16 ultraviolet bands below 350 nm did exactly that).
#: Those bands are dropped from the ISOFIT inputs and from the products.
RT_RANGE = (350.0, 2500.0)

#: JPL band names for the obs file, in the order ISOFIT indexes them.
OBS_BANDS = (
    "Path length (m)",
    "To-sensor azimuth (0 to 360 degrees cw from N)",
    "To-sensor zenith (0 to 90 degrees from zenith)",
    "To-sun azimuth (0 to 360 degrees cw from N)",
    "To-sun zenith (0 to 90 degrees from zenith)",
    "Solar phase",
    "Slope",
    "Aspect",
    "Cosine(i)",
    "UTC Time",
    "Earth-sun distance (AU)",
)
LOC_BANDS = ("Longitude (WGS-84)", "Latitude (WGS-84)", "Elevation (m)")

_ENVI_DTYPE = {"float32": 4, "float64": 5, "int16": 2, "int32": 3, "uint8": 1}


@dataclass(frozen=True)
class SensorSpec:
    """How one hyperproc sensor maps onto ``apply_oe``.

    Attributes:
        code: the ``sensor`` argument of ``apply_oe``. ``"NA"`` means the
            generic route, where the code becomes ``NA-YYYYMMDD``.
        unit_factor: multiply hyperproc radiance by this to get
            µW cm⁻² nm⁻¹ sr⁻¹. None means the conversion needs more than a
            factor and is not implemented yet.
        fid: ``strftime`` pattern that builds the file id ISOFIT will slice
            and parse back. ``{dt}`` in ``rdn`` marks where it goes.
        rdn: pattern of the radiance file name, so ISOFIT's slicing of the
            name yields exactly ``fid``.
        altitude_km: nominal platform altitude, used only when the product
            carries no path-length layer.
        tested: whether this route has been run through ISOFIT on a real
            granule and the reflectance compared against the provider's own
            product. A False entry only warns; it changes nothing else.
    """
    code: str
    unit_factor: float | None
    fid: str
    rdn: str = "{fid}_rdn"
    altitude_km: float | None = None
    tested: bool = False
    #: how radiance is obtained when a plain factor is not enough
    converter: str | None = None
    #: regex a provider granule id matches; when it does, that id is the fid
    id_pattern: str | None = None
    #: fit windows (nm) to pass to apply_oe instead of ISOFIT's per-sensor defaults
    inversion_windows: tuple | None = None
    #: name of a band grid ISOFIT imposes for this sensor (see :data:`BAND_GRIDS`)
    band_grid: str | None = None


SENSORS: dict[str, SensorSpec] = {
    "EMIT": SensorSpec("emit", 1.0, "emit%Y%m%dt%H%M%S", altitude_km=420.0, tested=True),
    # the AVIRIS readers carry JPL's own line id in attrs["granule"]; it wins over the
    # datetime pattern, whose seconds can differ from the id by one
    "AVIRIS-3": SensorSpec("av3", 1.0, "AV3%Y%m%dt%H%M%S", id_pattern=r"^AV3\d{8}t\d{6}", tested=True),
    "AVIRIS-5": SensorSpec("av5", 1.0, "AV5%Y%m%dt%H%M%S", id_pattern=r"^AV5\d{8}t\d{6}", tested=True),
    "AVIRIS-NG": SensorSpec("ang", 1.0, "ang%Y%m%dt%H%M%S", id_pattern=r"^ang\d{8}t\d{6}", tested=True),
    # apply_oe reads only the date from a Classic id (f<yymmdd>t..p..r..).
    "AVIRIS-CLASSIC": SensorSpec("avcl", 1.0, "f%y%m%dt01p00r01", id_pattern=r"^f\d{6}t\d{2}p\d{2}r\d{2}",
                                 tested=True),
    # NEON is the only entry never run through ISOFIT: the DP1 product on disk is
    # reflectance, not radiance, so there is nothing here to correct yet. It keeps
    # tested=False, which is what the warning is for.
    "NEON": SensorSpec("neon", 1.0, "NIS01_%Y%m%d_%H%M%S"),
    # EnMAP: fid = name.split("_")[5], parsed as %Y%m%dt%H%M%S.
    "ENMAP": SensorSpec("enmap", 100.0, "%Y%m%dt%H%M%S", rdn="ENMAP_L1B_hyperproc_0_0_{fid}_rdn",
                        altitude_km=653.0, tested=True),
    # PRISMA: fid = name.split("_")[1], parsed as %Y%m%d%H%M%S. L1 radiance is
    # W m-2 sr-1 um-1 (DN / ScaleFactor - Offset), hence x0.1.
    # The SWIR edge above 2470 nm rounds to DN 0 on up to half the pixels, so the
    # fit stops there; the water windows follow ISOFIT's defaults.
    "PRISMA": SensorSpec("prisma", 0.1, "%Y%m%d%H%M%S", rdn="PRS_{fid}_rdn", altitude_km=615.0, tested=True,
                         inversion_windows=((400.0, 1340.0), (1450.0, 1800.0), (1970.0, 2470.0))),
    # Tanager: fid = name[:23], time = fid[:15] as %Y%m%d_%H%M%S.
    "TANAGER": SensorSpec("tanager", 0.1, "%Y%m%d_%H%M%S_tanager", altitude_km=500.0, tested=True),
    # PACE OCI: fid = name[:24], time = fid[9:24] as %Y%m%dT%H%M%S. The reader
    # gives TOA reflectance rhot = Lt pi d2 / (F0 cos sza); the converter undoes
    # it with the per-band F0 and the distance factor stored in the L1B file.
    "PACE": SensorSpec("oci", 1.0, "PACE_OCI.%Y%m%dT%H%M%S", altitude_km=676.5, converter="pace_rhot",
                       band_grid="oci_rsr", tested=True),
    # DESIS has no apply_oe code: generic route, fid is the whole file stem.
    "DESIS": SensorSpec("NA", 1.0, "desis%Y%m%dt%H%M%S", rdn="{fid}", altitude_km=400.0, tested=True),
}

_ALIASES = {"AVIRIS3": "AVIRIS-3", "AVIRIS5": "AVIRIS-5", "AVIRIS": "AVIRIS-3",
            "AVIRISNG": "AVIRIS-NG", "AVIRISCLASSIC": "AVIRIS-CLASSIC"}


def sensor_spec(ds: xr.Dataset) -> tuple[str, SensorSpec]:
    """The :data:`SENSORS` entry for ``ds``, keyed by its ``sensor`` attr."""
    raw = str(ds.attrs.get("sensor", ""))
    key = raw.upper().replace("_", "-")
    key = _ALIASES.get(key.replace("-", ""), key)
    if key not in SENSORS:
        raise ValueError(f"no ISOFIT route for sensor {raw!r}; known: {sorted(SENSORS)}")
    return key, SENSORS[key]


def acquisition_time(ds: xr.Dataset) -> datetime:
    """UTC acquisition time from ``attrs["datetime"]``."""
    raw = str(ds.attrs.get("datetime", ""))
    if not raw:
        raise ValueError("dataset has no 'datetime' attribute; ISOFIT needs the acquisition time")
    txt = raw.replace("Z", "+00:00")
    txt = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", txt)
    try:
        dt = datetime.fromisoformat(txt)
    except ValueError:
        dt = datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def names_for(ds: xr.Dataset) -> tuple[str, str, str]:
    """``(sensor_code, fid, radiance_file_name)`` for ``ds``."""
    _, spec = sensor_spec(ds)
    dt = acquisition_time(ds)
    fid = dt.strftime(spec.fid)
    if spec.id_pattern:
        m = re.match(spec.id_pattern, str(ds.attrs.get("granule", "")))
        if m:
            fid = m.group(0)
    code = spec.code if spec.code != "NA" else "NA-" + dt.strftime("%Y%m%d")
    return code, fid, spec.rdn.format(fid=fid)


@dataclass
class Inputs:
    """What :func:`prepare_inputs` wrote, and what the ISOFIT run needs to know."""
    work_dir: str
    sensor: str
    code: str
    fid: str
    rdn: str
    loc: str
    obs: str
    wavelengths: str
    shape: tuple          # (lines, samples, bands)
    unit_factor: float
    datetime: str
    stem: str
    granule: str
    window: dict | None = None
    #: band positions of the source dataset that were written, when bands
    #: outside :data:`RT_RANGE` had to be dropped; None means all of them.
    bands: list | None = None
    stats: dict = field(default_factory=dict)

    def subset(self, ds):
        """Apply this run's window and band selection to a dataset."""
        ds, _ = _apply_window(ds, self.window)
        return ds if self.bands is None else ds.isel(wavelength=self.bands)

    def output(self, product: str) -> Path:
        """Path of an ``apply_oe`` product (``rfl``, ``uncert``, ``lbl``,
        ``state``, ``h2o``, ``atm_interp``, ``subs_state`` ...), named the way
        ISOFIT names them from the radiance file."""
        name = (self.fid + "_rdn").replace("_rdn", "_" + product)
        return Path(self.work_dir) / "output" / name

    @property
    def json(self) -> Path:
        return Path(self.work_dir) / "input" / "inputs.json"

    def save(self) -> Path:
        self.json.parent.mkdir(parents=True, exist_ok=True)
        self.json.write_text(json.dumps(asdict(self), indent=2, default=str))
        return self.json

    @classmethod
    def load(cls, work_dir: str | Path) -> "Inputs":
        """Read ``<work_dir>/input/inputs.json``, rebased onto ``work_dir``.

        The file stores absolute paths, so a work directory that was moved or
        copied would otherwise point every read back at the original and two
        different runs would silently return the same products.
        """
        work = Path(work_dir).expanduser().resolve()
        d = json.loads((work / "input" / "inputs.json").read_text())
        d["shape"] = tuple(d["shape"])
        d["work_dir"] = str(work)
        for key in ("rdn", "loc", "obs", "wavelengths"):
            if d.get(key):
                d[key] = str(work / "input" / Path(d[key]).name)
        return cls(**d)

    def describe(self) -> str:
        ny, nx, nb = self.shape
        s = self.stats
        lines = [f"ISOFIT inputs for {self.granule}  (sensor code {self.code}, fid {self.fid})",
                 f"  {ny} lines x {nx} samples x {nb} bands, radiance x{self.unit_factor:g} -> uW/cm2/nm/sr",
                 f"  rdn {self.rdn}", f"  loc {self.loc}", f"  obs {self.obs}"]
        if s:
            lines.append(f"  valid pixels {s.get('valid_fraction', float('nan')):.1%}; "
                         f"lat {s.get('lat_mean', float('nan')):.3f} lon {s.get('lon_mean', float('nan')):.3f} "
                         f"elev {s.get('elev_min', float('nan')):.0f}..{s.get('elev_max', float('nan')):.0f} m")
            lines.append(f"  sza {s.get('sza_min', 0):.1f}..{s.get('sza_max', 0):.1f}  vza {s.get('vza_min', 0):.1f}.."
                         f"{s.get('vza_max', 0):.1f}  raa {s.get('raa_min', 0):.0f}..{s.get('raa_max', 0):.0f} deg  "
                         f"utc {s.get('utc_mean', 0):.3f} h")
        return "\n".join(lines)


# --- ENVI writing -----------------------------------------------------------

def hdr_path(binary: Path | str) -> Path:
    """The ENVI header beside a binary: ``<file>.hdr``.

    Not ``Path.with_suffix(".hdr")``: a PACE file id carries a dot
    (``PACE_OCI.20260422T195047_rdn``), so that would write ``PACE_OCI.hdr``
    and ISOFIT would not find a header at all.
    """
    binary = Path(binary)
    return binary.with_name(binary.name + ".hdr")


def write_envi_header(path: Path, lines: int, samples: int, bands: int, dtype: str,
                      description: str = "", band_names=None, wavelength=None, fwhm=None,
                      extra: dict | None = None) -> Path:
    """Write ``path`` (the ``.hdr``) for a BIL cube, little-endian."""
    out = ["ENVI", f"description = {{{description}}}", f"samples = {samples}", f"lines = {lines}",
           f"bands = {bands}", "header offset = 0", "file type = ENVI Standard",
           f"data type = {_ENVI_DTYPE[dtype]}", "interleave = bil", "byte order = 0",
           f"data ignore value = {FILL:g}"]
    if band_names is not None:
        out.append("band names = {" + ", ".join(str(b) for b in band_names) + "}")
    if wavelength is not None:
        out.append("wavelength units = Nanometers")
        out.append("wavelength = {" + ", ".join(f"{float(w):.4f}" for w in wavelength) + "}")
    if fwhm is not None:
        out.append("fwhm = {" + ", ".join(f"{float(f):.4f}" for f in fwhm) + "}")
    for k, v in (extra or {}).items():
        out.append(f"{k} = {v}")
    path.write_text("\n".join(out) + "\n")
    return path


def _row_blocks(da: xr.DataArray, target_bytes: int = 256 * 2**20):
    """Row ranges that follow the dask chunking of ``da`` where it has one."""
    ny = da.sizes["y"]
    per_row = da.sizes["x"] * (da.sizes.get("wavelength", 1)) * 4
    rows = int(np.clip(target_bytes // max(per_row, 1), 1, ny))
    chunks = getattr(da.data, "chunks", None)
    if chunks:
        edges = np.cumsum((0,) + tuple(chunks[da.get_axis_num("y")]))
        # merge source chunks up to the target size, never split one
        starts, s = [0], 0
        for e in edges[1:]:
            if e - s >= rows:
                starts.append(int(e)); s = int(e)
        if starts[-1] != ny:
            starts.append(ny)
        return [(starts[i], starts[i + 1]) for i in range(len(starts) - 1)]
    return [(y0, min(y0 + rows, ny)) for y0 in range(0, ny, rows)]


def _write_cube(da: xr.DataArray, path: Path, factor: float, verbose: bool,
                band_scale: np.ndarray | None = None, pixel_scale: np.ndarray | None = None) -> None:
    """Stream ``da (y, x, wavelength)`` to ``path`` as BIL float32, NaN -> FILL.

    ``band_scale (wavelength,)`` and ``pixel_scale (y, x)`` multiply in as
    well; they turn a TOA reflectance into radiance without a second pass.
    """
    blocks = _row_blocks(da)
    with open(path, "wb") as fh:
        for i, (y0, y1) in enumerate(blocks):
            blk = da.isel(y=slice(y0, y1)).transpose("y", "wavelength", "x").values.astype(np.float32)
            if factor != 1.0:
                blk *= np.float32(factor)
            if band_scale is not None:
                blk *= np.asarray(band_scale, np.float32)[None, :, None]
            if pixel_scale is not None:
                blk *= np.asarray(pixel_scale[y0:y1], np.float32)[:, None, :]
            np.nan_to_num(blk, copy=False, nan=FILL, posinf=FILL, neginf=FILL)
            np.ascontiguousarray(blk, dtype="<f4").tofile(fh)
            if verbose and (i % max(1, len(blocks) // 8) == 0 or i == len(blocks) - 1):
                print(f"    rdn rows {y1}/{da.sizes['y']}", flush=True)


def _write_layers(arrs: list[np.ndarray], path: Path) -> None:
    """Write 2-D float64 layers as a BIL cube, NaN -> FILL."""
    cube = np.stack(arrs, axis=1).astype("<f8")   # (y, band, x)
    np.nan_to_num(cube, copy=False, nan=FILL, posinf=FILL, neginf=FILL)
    np.ascontiguousarray(cube).tofile(path)


# --- geometry assembly -------------------------------------------------------

def _layer(ds: xr.Dataset, name: str) -> np.ndarray | None:
    if name not in ds:
        return None
    arr = ds[name]
    if arr.ndim != 2:
        return None
    return np.asarray(arr.values, dtype="float64")


def _latlon(ds: xr.Dataset) -> tuple[np.ndarray, np.ndarray]:
    lat, lon = _layer(ds, "lat"), _layer(ds, "lon")
    if lat is not None and lon is not None:
        return lat, lon
    from hyperproc.grid import latlon_grid
    lat, lon = latlon_grid(ds)
    return np.asarray(lat, "float64"), np.asarray(lon, "float64")


def _phase(sza, vza, saa, vaa):
    s, v, d = np.deg2rad(sza), np.deg2rad(vza), np.deg2rad(vaa - saa)
    return np.rad2deg(np.arccos(np.clip(np.cos(s) * np.cos(v) + np.sin(s) * np.sin(v) * np.cos(d), -1, 1)))


def _earth_sun_au(dt: datetime) -> float:
    doy = dt.timetuple().tm_yday
    return 1.0 - 0.01672 * np.cos(np.deg2rad(0.9856 * (doy - 4)))


def assemble_obs(ds: xr.Dataset, spec: SensorSpec, dt: datetime) -> list[np.ndarray]:
    """The eleven obs layers, float64, NaN where unknown."""
    need = {k: _layer(ds, k) for k in ("sza", "saa", "vza", "vaa")}
    missing = [k for k, v in need.items() if v is None]
    if missing:
        raise ValueError(f"dataset lacks the geometry layers {missing}; ISOFIT needs sun and view angles per pixel")
    sza, saa, vza, vaa = (need[k] for k in ("sza", "saa", "vza", "vaa"))
    shape = sza.shape
    path = _layer(ds, "path_length")
    if path is None:
        if spec.altitude_km is None:
            raise ValueError("dataset has no path_length layer and the sensor has no nominal altitude")
        elev = _layer(ds, "elev")
        elev = np.zeros(shape) if elev is None else np.nan_to_num(elev, nan=0.0)
        path = (spec.altitude_km * 1000.0 - elev) / np.clip(np.cos(np.deg2rad(vza)), 1e-3, None)
    phase = _layer(ds, "solar_phase")
    if phase is None:
        phase = _phase(sza, vza, saa, vaa)
    slope = _layer(ds, "slope")
    aspect = _layer(ds, "aspect")
    cos_i = _layer(ds, "cos_i")
    if slope is None:
        slope = np.zeros(shape)
    if aspect is None:
        aspect = np.zeros(shape)
    if cos_i is None:
        cos_i = np.cos(np.deg2rad(sza))
    utc = _layer(ds, "utc_time")
    if utc is None:
        utc = np.full(shape, dt.hour + dt.minute / 60 + dt.second / 3600.0)
    au = _layer(ds, "earth_sun_distance")
    if au is None:
        au = np.full(shape, _earth_sun_au(dt))
    return [path, vaa % 360.0, vza, saa % 360.0, sza, phase, slope, aspect, cos_i, utc, au]


def assemble_loc(ds: xr.Dataset) -> list[np.ndarray]:
    """Longitude, latitude, elevation layers, float64."""
    lat, lon = _latlon(ds)
    elev = _layer(ds, "elev")
    if elev is None:
        raise ValueError("dataset has no 'elev' layer; ISOFIT needs surface elevation per pixel "
                         "(a DEM provider for products without one is a later step)")
    return [lon, lat, elev]


def _apply_window(ds: xr.Dataset, window):
    if window is None:
        return ds, None
    if isinstance(window, dict):
        sel = {k: (slice(*v) if isinstance(v, (tuple, list)) else v) for k, v in window.items()}
    else:
        (y0, y1), (x0, x1) = window
        sel = {"y": slice(y0, y1), "x": slice(x0, x1)}
    rec = {k: [v.start, v.stop] for k, v in sel.items()}
    return ds.isel(**sel), rec


def _stats(obs: list[np.ndarray], loc: list[np.ndarray], rdn_first: np.ndarray) -> dict:
    def rng(a):
        a = a[np.isfinite(a)]
        return (float(a.min()), float(a.max())) if a.size else (float("nan"), float("nan"))
    path, vaa, vza, saa, sza, *_rest, utc, _au = obs
    lon, lat, elev = loc
    raa = np.abs(vaa - saa) % 360.0
    raa = np.minimum(raa, 360.0 - raa)
    out = {"valid_fraction": float(np.isfinite(rdn_first).mean()),
           "lat_mean": float(np.nanmean(lat)), "lon_mean": float(np.nanmean(lon)),
           "elev_mean": float(np.nanmean(elev)), "utc_mean": float(np.nanmean(utc)),
           "path_mean_km": float(np.nanmean(path)) / 1000.0}
    for k, a in (("elev", elev), ("sza", sza), ("vza", vza), ("raa", raa), ("saa", saa), ("vaa", vaa)):
        out[f"{k}_min"], out[f"{k}_max"] = rng(a)
    return out


# --- radiance converters -------------------------------------------------------

def oci_rsr_bands() -> np.ndarray:
    """Band centres (nm) of the OCI response functions ISOFIT resamples with.

    For the ``oci`` sensor ISOFIT replaces its Gaussian resampling with the
    measured response functions in ``data/oci/pace_oci_rsr.nc``, whose 270
    bands are its own idea of the instrument. Handing it a different band
    count makes the look-up table and the instrument model disagree
    ("conflicting sizes for dimension 'wl'"), so the inputs are written on
    this grid.
    """
    import h5py
    from isofit.data import env

    with h5py.File(Path(env.data) / "oci" / "pace_oci_rsr.nc", "r") as h:
        return np.asarray(h["bands"][:], dtype="float64")


#: Band grids some sensors must be written on, name -> callable returning the centres in nm.
BAND_GRIDS = {"oci_rsr": oci_rsr_bands}


def match_bands(wl: np.ndarray, grid: np.ndarray, tol: float = 2.0) -> list:
    """Positions in ``wl`` nearest to each wavelength of ``grid``.

    Raises when a grid band has no match within ``tol`` nm or two grid bands
    claim the same one, which would mean the product is not the instrument
    the grid describes.
    """
    idx = [int(np.argmin(np.abs(wl - g))) for g in grid]
    off = np.abs(wl[idx] - grid)
    if off.max() > tol or len(set(idx)) != len(idx):
        raise ValueError(f"cannot match this product's {wl.size} bands to the sensor's {grid.size}-band "
                         f"grid (largest offset {off.max():.2f} nm, {len(idx) - len(set(idx))} collisions)")
    return idx


def pace_rhot_scales(ds: xr.Dataset):
    """Per-band and per-pixel factors turning OCI ``rhot`` into µW cm-2 nm-1 sr-1.

    The L1B stores ``rhot = Lt * pi * d2 / (F0 * cos(sza))`` with ``F0`` in
    W m-2 um-1 per band and ``d2`` (``earth_sun_distance_correction``) as a
    global attribute; ``band_index`` says which F0 each band of the sorted
    cube came from. So ``Lt = rhot * F0 * cos(sza) / (pi * d2) * 0.1``.
    """
    import h5py
    src = ds.attrs.get("source")
    if not src or not Path(src).is_file():
        raise ValueError("PACE radiance conversion needs the L1B file (attrs['source']) for F0")
    with h5py.File(src, "r") as h:
        f0 = np.concatenate([h[f"sensor_band_parameters/{arm}_solar_irradiance"][:].astype("float64")
                             for arm in ("blue", "red", "SWIR")])
        d2 = float(np.ravel(h.attrs["earth_sun_distance_correction"])[0])
    bi = np.asarray(ds["band_index"].values, int)
    band_scale = f0[bi] * 0.1 / (np.pi * d2)
    pixel_scale = np.cos(np.deg2rad(np.asarray(ds["sza"].values, "float64")))
    return band_scale.astype("float32"), pixel_scale.astype("float32")


CONVERTERS = {"pace_rhot": pace_rhot_scales}


# --- entry point -------------------------------------------------------------

def prepare_inputs(ds: xr.Dataset, work_dir: str | Path, window=None,
                   overwrite: bool = False, verbose: bool = True, dem: bool = True) -> Inputs:
    """Write the ``_rdn``, ``_loc`` and ``_obs`` files for ``ds`` under ``work_dir/input``.

    Args:
        ds: a hyperproc **L1B radiance** dataset (any sensor in :data:`SENSORS`).
            Reflectance products are refused.
        work_dir: the ISOFIT working directory; ``input/`` is created inside it.
        window: optional subset, ``{"y": (y0, y1), "x": (x0, x1)}`` or
            ``((y0, y1), (x0, x1))``, for validation runs on a piece of a scene.
        overwrite: rewrite files that already exist with the right shape.
        dem: when the dataset has no ``elev`` layer, sample one from the
            Copernicus DEM (:func:`hyperproc.atmos.dem.add_elevation`).

    Returns:
        :class:`Inputs` with every path, the ISOFIT sensor code and file id,
        and summary statistics of the geometry. Also saved as
        ``input/inputs.json`` so a later step can pick the run up.
    """
    var = main_var(ds)
    level = str(ds.attrs.get("level", ""))
    key, spec = sensor_spec(ds)
    if not level.upper().startswith("L1") or (var != "radiance" and spec.converter is None):
        raise ValueError(f"atmospheric correction needs an L1B radiance dataset; got {var!r} at level {level!r}")
    if spec.unit_factor is None:
        raise NotImplementedError(f"{key}: radiance conversion for ISOFIT is not implemented yet")
    if not spec.tested:
        warnings.warn(f"{key}: the ISOFIT input route has not been validated end to end yet", stacklevel=2)
    dt = acquisition_time(ds)
    code, fid, rdn_name = names_for(ds)
    ds, win = _apply_window(ds, window)
    wl_all = np.asarray(ds["wavelength"].values, "float64")
    bands = None
    if spec.band_grid:
        bands = match_bands(wl_all, BAND_GRIDS[spec.band_grid]())
        if verbose:
            print(f"  {len(bands)} of {wl_all.size} bands selected onto ISOFIT's {spec.band_grid} grid")
        ds = ds.isel(wavelength=bands)
        wl_all = np.asarray(ds["wavelength"].values, "float64")
    inside = (wl_all >= RT_RANGE[0]) & (wl_all <= RT_RANGE[1])
    if not inside.all():
        if not inside.any():
            raise ValueError(f"no band of this dataset lies in {RT_RANGE[0]:g}-{RT_RANGE[1]:g} nm, "
                             "the range the radiative transfer covers")
        keep = np.flatnonzero(inside).tolist()
        bands = [bands[i] for i in keep] if bands is not None else keep
        dropped = wl_all[~inside]
        warnings.warn(f"{len(dropped)} band(s) outside {RT_RANGE[0]:g}-{RT_RANGE[1]:g} nm dropped "
                      f"({dropped.min():.1f}-{dropped.max():.1f} nm): the radiative-transfer engines "
                      "cannot simulate them", stacklevel=2)
        ds = ds.isel(wavelength=bands)
    if dem and "elev" not in ds:
        from hyperproc.atmos.dem import add_elevation
        add_elevation(ds, verbose=verbose)
    ny, nx, nb = ds.sizes["y"], ds.sizes["x"], ds.sizes["wavelength"]

    work = Path(work_dir).expanduser().resolve()
    inp = work / "input"
    inp.mkdir(parents=True, exist_ok=True)
    rdn, loc, obs = inp / rdn_name, inp / f"{fid}_loc", inp / f"{fid}_obs"
    wl = np.asarray(ds["wavelength"].values, "float64")
    fwhm = np.asarray(ds["fwhm"].values, "float64") if "fwhm" in ds.coords else np.gradient(wl)
    wl_txt = inp / "wavelengths.txt"
    np.savetxt(wl_txt, np.column_stack([np.arange(nb), wl, fwhm]), fmt=["%d", "%.4f", "%.4f"])

    def fresh(p: Path, nbands: int, itemsize: int) -> bool:
        return p.is_file() and hdr_path(p).is_file() and p.stat().st_size == ny * nx * nbands * itemsize

    desc = f"hyperproc {key} {ds.attrs.get('granule', ds.attrs.get('stem', ''))}"
    if verbose:
        print(f"prepare_inputs: {key} -> apply_oe sensor {code}, fid {fid}; {ny} x {nx} x {nb}")
    obs_layers = assemble_obs(ds, spec, dt)
    loc_layers = assemble_loc(ds)
    if overwrite or not fresh(loc, 3, 8):
        _write_layers(loc_layers, loc)
        write_envi_header(hdr_path(loc), ny, nx, 3, "float64", desc + " loc", LOC_BANDS)
    if overwrite or not fresh(obs, len(OBS_BANDS), 8):
        _write_layers(obs_layers, obs)
        write_envi_header(hdr_path(obs), ny, nx, len(OBS_BANDS), "float64", desc + " obs", OBS_BANDS)
    band_scale = pixel_scale = None
    if spec.converter:
        band_scale, pixel_scale = CONVERTERS[spec.converter](ds)
    if overwrite or not fresh(rdn, nb, 4):
        if verbose:
            print(f"  writing radiance ({ny * nx * nb * 4 / 2**30:.2f} GB){' from TOA reflectance' if spec.converter else ''} ...", flush=True)
        _write_cube(ds[var], rdn, spec.unit_factor, verbose, band_scale=band_scale, pixel_scale=pixel_scale)
        write_envi_header(hdr_path(rdn), ny, nx, nb, "float32", desc + " rdn",
                          wavelength=wl, fwhm=fwhm,
                          extra={"radiance units": "uW/cm2/nm/sr", "sensor type": key,
                                 "acquisition time": dt.strftime("%Y-%m-%dT%H:%M:%SZ")})
    elif verbose:
        print("  radiance file already present with the right size; kept")
    first = np.asarray(ds[var].isel(wavelength=min(nb - 1, 60)).values, "float64")
    stats = _stats(obs_layers, loc_layers, first)
    # ISOFIT treats -9999 as a measured radiance unless the whole spectrum is
    # missing; a spectrum with only some channels missing comes back as
    # reflectance in the hundreds. Count them so the problem is visible.
    rdn_mm = np.memmap(rdn, dtype="<f4", mode="r", shape=(ny, nb, nx))
    step = max(1, ny // 64)
    probe = rdn_mm[::step] <= FILL + 1.0                      # (rows, band, x)
    partial = probe.any(axis=1) & ~probe.all(axis=1)
    stats["partial_fill_fraction"] = float(partial.mean())
    if partial.mean() > 0.001:
        warnings.warn(f"{partial.mean():.1%} of spectra have some but not all bands missing; ISOFIT will invert "
                      "those to nonsense. Check the reader's fill handling for this product.", stacklevel=2)
    out = Inputs(work_dir=str(work), sensor=key, code=code, fid=fid, rdn=str(rdn), loc=str(loc), obs=str(obs),
                 wavelengths=str(wl_txt), shape=(ny, nx, nb), unit_factor=spec.unit_factor,
                 datetime=dt.strftime("%Y-%m-%dT%H:%M:%SZ"), stem=str(ds.attrs.get("stem", "")),
                 granule=str(ds.attrs.get("granule", "")), window=win, bands=bands,
                 stats={**stats, "elev_source": str(ds.attrs.get("elev_source", "product")),
                        "radiance_source": spec.converter or "product"})
    out.save()
    if verbose:
        print(out.describe())
    return out
