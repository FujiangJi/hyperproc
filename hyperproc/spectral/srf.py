"""Spectral response functions for common instruments, fetched and cached.

Convolving a hyperspectral cube onto a broadband sensor is only as good as the
response you convolve with. For most instruments the real, measured response is
published, and this module goes and gets it::

    from hyperproc.spectral import srf
    print(srf.available())                  # what is known, and what is cached
    s2 = srf.fetch("SENTINEL2A")            # downloads once, then reads the cache
    hp.resample(ds, sensor="LANDSAT8")      # the same thing, through resample

Downloads land in ``$HYPERPROC_CACHE_DIR/srf`` as the original spreadsheet plus
a parsed ``.npz``, so the network is touched once per instrument.

Measured, or nominal
--------------------
Two kinds of entry, and the difference is recorded in ``kind`` rather than left
for you to guess:

``measured``
    A tabulated response per band, from the agency. Sentinel-2 MSI from ESA,
    Landsat TM, ETM+, OLI and OLI-2 from the USGS spectral viewer.
``nominal``
    Only published band edges, turned into centres and widths. PlanetScope is
    here because Planet publishes band ranges rather than response curves. A
    nominal entry is used with a Gaussian response, which on PACE's measured
    bands differs from the real curve by about 0.2 % in the median, so it is a
    fair approximation but it is not the instrument.

Bands whose response falls outside the source's coverage come back NaN from
:func:`hyperproc.spectral.resample`, which matters here: simulating Sentinel-2
band 10 (1375 nm cirrus) from EMIT cannot work, because that wavelength sits in
a water-vapour gap EMIT does not measure.
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

import numpy as np

__all__ = ["SOURCES", "NOMINAL", "ALIASES", "available", "fetch", "target", "cache_dir", "resolve"]

_S2 = ("https://sentinels.copernicus.eu/documents/247904/685211/"
       "S2-SRF_COPE-GSEG-EOPG-TN-15-0007_3.1.xlsx")
_USGS = "https://landsat.usgs.gov/landsat/spectral_viewer/bands/"

#: Instruments whose measured response is published and machine readable.
SOURCES: dict[str, dict] = {
    "SENTINEL2A": {"url": _S2, "parser": "sentinel2", "sheet": "Spectral Responses (S2A)",
                   "label": "Sentinel-2A MSI", "agency": "ESA"},
    "SENTINEL2B": {"url": _S2, "parser": "sentinel2", "sheet": "Spectral Responses (S2B)",
                   "label": "Sentinel-2B MSI", "agency": "ESA"},
    "LANDSAT4":   {"url": _USGS + "L4_TM_RSR.xlsx", "parser": "landsat",
                   "label": "Landsat 4 TM", "agency": "USGS"},
    "LANDSAT5":   {"url": _USGS + "L5_TM_RSR.xlsx", "parser": "landsat",
                   "label": "Landsat 5 TM", "agency": "USGS"},
    "LANDSAT7":   {"url": _USGS + "L7_ETM_RSR.xlsx", "parser": "landsat",
                   "label": "Landsat 7 ETM+", "agency": "USGS"},
    "LANDSAT8":   {"url": _USGS + "L8_OLI_RSR.xlsx", "parser": "landsat",
                   "label": "Landsat 8 OLI", "agency": "USGS"},
    "LANDSAT9":   {"url": _USGS + "L9_OLI2_RSR.xlsx", "parser": "landsat",
                   "label": "Landsat 9 OLI-2", "agency": "USGS"},
}

#: Instruments published as band edges only (nm), used with a Gaussian response.
NOMINAL: dict[str, dict] = {
    "PLANETSCOPE4": {"label": "PlanetScope 4-band (PS2 / Dove)", "agency": "Planet",
                     "bands": {"Blue": (455, 515), "Green": (500, 590),
                               "Red": (590, 670), "NIR": (780, 860)}},
    "PLANETSCOPE8": {"label": "PlanetScope 8-band (PSB.SD / SuperDove)", "agency": "Planet",
                     "bands": {"CoastalBlue": (431, 452), "Blue": (465, 515),
                               "GreenI": (513, 549), "Green": (547, 583),
                               "Yellow": (600, 620), "Red": (650, 680),
                               "RedEdge": (697, 713), "NIR": (845, 885)}},
}

ALIASES: dict[str, str] = {
    "S2": "SENTINEL2A", "S2A": "SENTINEL2A", "S2B": "SENTINEL2B", "SENTINEL2": "SENTINEL2A",
    "MSI": "SENTINEL2A", "SENTINEL-2": "SENTINEL2A", "SENTINEL-2A": "SENTINEL2A",
    "SENTINEL-2B": "SENTINEL2B",
    "L4": "LANDSAT4", "L5": "LANDSAT5", "L7": "LANDSAT7", "L8": "LANDSAT8", "L9": "LANDSAT9",
    "TM": "LANDSAT5", "ETM": "LANDSAT7", "ETM+": "LANDSAT7", "OLI": "LANDSAT8",
    "OLI2": "LANDSAT9", "OLI-2": "LANDSAT9",
    "LANDSAT-4": "LANDSAT4", "LANDSAT-5": "LANDSAT5", "LANDSAT-7": "LANDSAT7",
    "LANDSAT-8": "LANDSAT8", "LANDSAT-9": "LANDSAT9",
    "PLANETSCOPE": "PLANETSCOPE4", "PS": "PLANETSCOPE4", "PS2": "PLANETSCOPE4",
    "DOVE": "PLANETSCOPE4", "SUPERDOVE": "PLANETSCOPE8", "PSB.SD": "PLANETSCOPE8",
    "PLANETSCOPE-4": "PLANETSCOPE4", "PLANETSCOPE-8": "PLANETSCOPE8",
}

_UA = {"User-Agent": "Mozilla/5.0 (hyperproc spectral response fetcher)"}
SQRT_8LN2 = 2.3548200450309493


def cache_dir() -> Path:
    d = Path(os.environ.get("HYPERPROC_CACHE_DIR", "~/.cache/hyperproc")).expanduser() / "srf"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve(sensor: str) -> str:
    """The canonical key for a sensor name, accepting the usual spellings."""
    key = re.sub(r"[\s_]+", "", str(sensor)).upper()
    key = ALIASES.get(key, key)
    if key not in SOURCES and key not in NOMINAL:
        raise ValueError(f"unknown sensor {sensor!r}. Known: "
                         f"{sorted(set(SOURCES) | set(NOMINAL))}, plus the aliases "
                         f"{sorted(ALIASES)}")
    return key


# --------------------------------------------------------------------------- #
# parsing what the agencies publish                                            #
# --------------------------------------------------------------------------- #

def _load_workbook(path: Path):
    try:
        import openpyxl
    except ImportError as exc:                      # pragma: no cover - environment dependent
        raise ImportError(
            "reading a published response function needs openpyxl:\n    pip install openpyxl\n"
            "Sentinel-2 and Landsat both publish theirs as spreadsheets."
        ) from exc
    return openpyxl.load_workbook(path, read_only=True, data_only=True)


def _to_nm(wl: np.ndarray) -> np.ndarray:
    """Some sheets are in micrometres; anything under 100 cannot be nanometres."""
    wl = np.asarray(wl, dtype="float64")
    return wl * 1000.0 if np.nanmax(wl) < 100.0 else wl


def _parse_sentinel2(path: Path, sheet: str) -> dict:
    wb = _load_workbook(path)
    if sheet not in wb.sheetnames:
        raise ValueError(f"{path.name} has no sheet {sheet!r}; found {wb.sheetnames}")
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = [str(c) for c in rows[0] if c is not None]
    names = [h.split("_")[-1] for h in header[1:]]              # S2A_SR_AV_B8A -> B8A
    data = np.array([[np.nan if c is None else c for c in r[:len(header)]]
                     for r in rows[1:] if r[0] is not None], dtype="float64")
    return {"fine_wl": _to_nm(data[:, 0]), "response": data[:, 1:].T, "bands": names}


def _parse_landsat(path: Path, sheet=None) -> dict:
    wb = _load_workbook(path)
    fine, resp, names, order = None, [], [], []
    for name in wb.sheetnames:
        ws = wb[name]
        if not hasattr(ws, "iter_rows"):
            continue                                            # chart sheets
        rows = list(ws.iter_rows(values_only=True))
        if not rows or not rows[0] or len(rows[0]) < 2:
            continue
        if str(rows[0][0]).strip().lower() != "wavelength":
            continue                                            # README, Band summary
        pairs = [(r[0], r[1]) for r in rows[1:]
                 if r and isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        if len(pairs) < 5:
            continue
        wl = _to_nm(np.array([q[0] for q in pairs], dtype="float64"))
        r = np.clip(np.array([q[1] for q in pairs], dtype="float64"), 0.0, None)
        # Landsat 4-8 label the column "Band N", Landsat 9 labels it "BA RSR [watts]";
        # fall back to spectral order when the official number is not written down.
        m = re.search(r"band\s*(\d+)", str(rows[0][1]), re.I)
        order.append(int(m.group(1)) if m else float(np.sum(r * wl) / max(np.sum(r), 1e-12)))
        names.append(name.split("-")[0])
        resp.append((wl, r))
    wb.close()
    if not resp:
        raise ValueError(f"no per-band response sheets found in {path.name}")
    lo = min(w.min() for w, _ in resp); hi = max(w.max() for w, _ in resp)
    fine = np.arange(np.floor(lo), np.ceil(hi) + 1.0, 1.0)      # a common 1 nm grid
    R = np.array([np.interp(fine, w, r, left=0.0, right=0.0) for w, r in resp])
    k = np.argsort(order)
    return {"fine_wl": fine, "response": R[k], "bands": [names[i] for i in k]}


def _summarise(fine_wl: np.ndarray, response: np.ndarray) -> tuple:
    """Response-weighted centre and half-maximum width of each band."""
    centres, fwhms = [], []
    for r in response:
        r = np.where(np.isfinite(r), r, 0.0)
        if r.max() <= 0:
            centres.append(np.nan); fwhms.append(np.nan); continue
        centres.append(float(np.sum(r * fine_wl) / np.sum(r)))
        half = fine_wl[r >= 0.5 * r.max()]
        fwhms.append(float(half.max() - half.min()))
    return np.array(centres), np.array(fwhms)


# --------------------------------------------------------------------------- #
# fetching                                                                     #
# --------------------------------------------------------------------------- #

def _download(url: str, path: Path, verbose: bool) -> Path:
    import requests
    if verbose:
        print(f"  downloading {url.rsplit('/', 1)[-1]} ...", flush=True)
    resp = requests.get(url, headers=_UA, timeout=300)
    resp.raise_for_status()
    if not resp.content.startswith(b"PK"):
        raise RuntimeError(f"{url} did not return a spreadsheet (got "
                           f"{resp.headers.get('content-type', 'unknown')}); the published "
                           "location may have moved")
    path.write_bytes(resp.content)
    return path


def fetch(sensor: str, cache: Path | None = None, overwrite: bool = False,
          verbose: bool = True) -> dict:
    """The response functions of ``sensor``, downloading and caching on first use.

    Args:
        sensor: an instrument name or alias; see :func:`available`.
        cache: where to keep the files; ``$HYPERPROC_CACHE_DIR/srf`` by default.
        overwrite: re-download even when the cache has it.
        verbose: say what is being fetched.

    Returns:
        dict with ``wavelength`` and ``fwhm`` per band, ``bands`` (names),
        ``label``, ``kind`` (``"measured"`` or ``"nominal"``) and, for a
        measured instrument, ``response`` ``(n_band, n_fine)`` on ``response_wl``.

    Raises:
        ValueError: unknown sensor.
        RuntimeError: the published file could not be retrieved.
    """
    key = resolve(sensor)
    if key in NOMINAL:
        spec = NOMINAL[key]
        edges = spec["bands"]
        wl = np.array([(a + b) / 2.0 for a, b in edges.values()], dtype="float64")
        fw = np.array([b - a for a, b in edges.values()], dtype="float64")
        return {"wavelength": wl, "fwhm": fw, "bands": list(edges), "label": spec["label"],
                "agency": spec["agency"], "kind": "nominal", "response": None, "response_wl": None}

    spec = SOURCES[key]
    root = Path(cache) if cache else cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    npz = root / f"{key}.npz"
    if npz.is_file() and not overwrite:
        z = np.load(npz, allow_pickle=False)
        names = [str(b) for b in np.load(npz, allow_pickle=True)["bands"]]
        if verbose:
            print(f"  {spec['label']} [cached] {npz.name}")
        return {"wavelength": z["wavelength"], "fwhm": z["fwhm"], "bands": names,
                "label": spec["label"], "agency": spec["agency"], "kind": "measured",
                "response": z["response"], "response_wl": z["response_wl"]}

    raw = root / spec["url"].rsplit("/", 1)[-1]
    if overwrite or not raw.is_file():
        _download(spec["url"], raw, verbose)
    parsed = (_parse_sentinel2(raw, spec["sheet"]) if spec["parser"] == "sentinel2"
              else _parse_landsat(raw))
    centres, fwhms = _summarise(parsed["fine_wl"], parsed["response"])
    np.savez_compressed(npz, wavelength=centres, fwhm=fwhms, response=parsed["response"],
                        response_wl=parsed["fine_wl"], bands=np.array(parsed["bands"], dtype=object))
    if verbose:
        print(f"  {spec['label']}: {len(centres)} bands, "
              f"{centres.min():.0f}-{centres.max():.0f} nm -> {npz.name}")
    return {"wavelength": centres, "fwhm": fwhms, "bands": parsed["bands"],
            "label": spec["label"], "agency": spec["agency"], "kind": "measured",
            "response": parsed["response"], "response_wl": parsed["fine_wl"]}


def target(sensor: str, **kwargs) -> dict:
    """A target description for :func:`hyperproc.spectral.target_grid`."""
    got = fetch(sensor, **kwargs)
    out = {"wavelength": got["wavelength"], "fwhm": got["fwhm"],
           "label": f"{got['label']} ({got['kind']})", "bands": got["bands"]}
    if got["kind"] == "measured":
        out.update(response=got["response"], response_wl=got["response_wl"], method="response")
    else:
        out.update(method="gaussian")
    return out


def available(cache: Path | None = None) -> str:
    """A table of the instruments known here, and which are already cached."""
    root = Path(cache) if cache else cache_dir()
    lines = [f"{'sensor':14s} {'kind':9s} {'bands':>5s}  {'cached':7s} source",
             f"{'-'*14} {'-'*9} {'-'*5}  {'-'*7} {'-'*40}"]
    for key, spec in SOURCES.items():
        hit = (root / f"{key}.npz")
        n = str(len(np.load(hit)["wavelength"])) if hit.is_file() else "-"
        lines.append(f"{key:14s} {'measured':9s} {n:>5s}  {'yes' if hit.is_file() else 'no':7s} "
                     f"{spec['agency']}")
    for key, spec in NOMINAL.items():
        lines.append(f"{key:14s} {'nominal':9s} {len(spec['bands']):5d}  {'n/a':7s} "
                     f"{spec['agency']} (band edges only)")
    return "\n".join(lines)
