"""Which reader handles which (sensor, level), and how to guess from a filename.

One table, one place to edit. Adding a sensor means writing its reader module
and flipping its ``loader`` entry here from ``None`` to the function.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Entry:
    """One supported (or planned) sensor/level combination."""

    sensor: str
    level: str
    #: Called as ``loader(path, **kwargs) -> xr.Dataset``. None = not written yet.
    loader: Callable | None
    #: What the user should hand to :func:`hyperproc.open`.
    expects: str
    #: Regexes matched against the filename to auto-detect this entry.
    patterns: tuple[str, ...] = ()
    note: str = ""

    @property
    def implemented(self) -> bool:
        return self.loader is not None

    def matches(self, name: str) -> bool:
        return any(re.match(p, name, re.IGNORECASE) for p in self.patterns)


def _tanager(path, **kw):
    from hyperproc.readers.tanager import open_tanager

    return open_tanager(path, **kw)


def _pace(path, **kw):
    from hyperproc.readers.pace import open_pace

    return open_pace(path, **kw)


def _enmap(path, **kw):
    from hyperproc.readers.enmap import open_enmap

    return open_enmap(path, **kw)


def _desis(path, **kw):
    from hyperproc.readers.desis import open_desis

    return open_desis(path, **kw)


def _neon(path, **kw):
    from hyperproc.readers.neon import open_neon

    return open_neon(path, **kw)


def _aviris(path, **kw):
    from hyperproc.readers.aviris import open_aviris

    return open_aviris(path, **kw)


def _prisma(path, **kw):
    from hyperproc.readers.prisma import open_prisma

    return open_prisma(path, **kw)


def _emit(path, **kw):
    # Imported lazily so a missing optional dependency for one sensor never
    # breaks `import hyperproc` for the others.
    from hyperproc.readers.emit import open_emit

    return open_emit(path, **kw)


#: The dispatch table. Keys are ``(SENSOR, LEVEL)``, both upper-case.
REGISTRY: dict[tuple[str, str], Entry] = {}


def register(entry: Entry) -> None:
    REGISTRY[(entry.sensor.upper(), entry.level.upper())] = entry


# --- implemented ---------------------------------------------------------

register(Entry(
    sensor="EMIT", level="L2A", loader=_emit,
    expects="EMIT_L2A_RFL_*.nc  (MASK and OBS siblings are picked up automatically)",
    patterns=(r"EMIT_L2A_RFL_.*\.nc$",),
))
register(Entry(
    sensor="EMIT", level="L1B", loader=_emit,
    expects="EMIT_L1B_RAD_*.nc  (OBS and MASK siblings are picked up automatically)",
    patterns=(r"EMIT_L1B_RAD_.*\.nc$",),
    note="at-sensor radiance in uW/cm^2/SR/nm; no good_wavelengths flag",
))

for _lvl, _note in [
    ("L2D", "geocoded surface reflectance on a UTM grid"),
    ("L2C", "geolocated surface reflectance, 1000x1000 swath, plus AOT/AEX/COT/WVM maps"),
    ("L2B", "geolocated at-surface radiance, 1000x1000 swath"),
    ("L1", "at-sensor radiance, 1000x1000 swath; angles/geolocation borrowed from an L2C/L2B "
           "sibling when present, else ephemeris; no elevation (see hyperproc.atmos.dem)"),
]:
    register(Entry(
        sensor="PRISMA", level=_lvl, loader=_prisma,
        expects=f"PRS_{_lvl}_STD_*.he5",
        patterns=(rf"PRS_{_lvl}_.*\.he5$",),
        note=_note,
    ))


for _lvl, _note in [
    ("L2A", "orthorectified surface reflectance, 30 m UTM"),
    ("L1C", "orthorectified at-sensor radiance, 30 m UTM"),
    ("L1B", "at-sensor radiance on the 1024x1024 sensor grid, no CRS"),
]:
    register(Entry(
        sensor="DESIS", level=_lvl, loader=_desis,
        expects=f"DESIS-HSI-{_lvl}-*-SPECTRAL_IMAGE.tif",
        patterns=(rf"DESIS-HSI-{_lvl}-.*-SPECTRAL_IMAGE\.tif$",),
        note=_note,
    ))


for _lvl, _note in [
    ("L2A", "orthorectified surface reflectance, 30 m UTM, 224 bands"),
    ("L1C", "orthorectified TOA radiance, 30 m UTM"),
    ("L1B", "TOA radiance, one detector per open (cube='vnir'|'swir'); VNIR/SWIR are "
     "not co-registered until L1C, so no merged cube and no CRS"),
]:
    register(Entry(
        sensor="ENMAP", level=_lvl, loader=_enmap,
        expects=f"ENMAP01-____{_lvl}-*-SPECTRAL_IMAGE[_VNIR|_SWIR][_COG].TIF",
        patterns=(rf"ENMAP01-_*{_lvl}-.*-SPECTRAL_IMAGE(_VNIR|_SWIR)?(_COG)?\.TIF$",),
        note=_note,
    ))


for _lvl, _pat, _note in [
    ("L2", r"PACE_OCI\..*\.L2\..*\.nc$",
     "SFREFL surface reflectance, 122 bands; ~1 km swath, geometry from the L1B sibling"),
    ("L1B", r"PACE_OCI\..*\.L1B\..*\.nc$",
     "TOA reflectance, 291 bands across blue/red/SWIR detectors, geometry in-file"),
]:
    register(Entry(
        sensor="PACE", level=_lvl, loader=_pace,
        expects=f"PACE_OCI.*.{_lvl}.*.nc",
        patterns=(_pat,),
        note=_note,
    ))


for _lvl, _pat, _note in [
    ("L2A", r".*_ortho_sr_hdf5\.h5$",
     "orthorectified surface reflectance, 426 bands, 30 m; HDF-EOS5 grid"),
    ("L1B", r".*_ortho_radiance_hdf5\.h5$",
     "orthorectified TOA radiance, W/(m^2 sr um); no good_wavelengths flag"),
]:
    register(Entry(
        sensor="TANAGER", level=_lvl, loader=_tanager,
        expects=f"*_ortho_{'sr' if _lvl == 'L2A' else 'radiance'}_hdf5.h5",
        patterns=(_pat,),
        note=_note,
    ))


# AVIRIS: one loader for four instruments. The reader works out which from the
# granule id, so `sensor="AVIRIS"` is enough; the per-instrument keys below are
# there for when you want to be explicit, and carry no patterns of their own so
# sniff() always resolves to the generic entry.
register(Entry(
    sensor="AVIRIS", level="L2A", loader=_aviris,
    expects="the reflectance cube, its .hdr, or the folder holding it - "
            "*_RFL_ORT (AVIRIS-3), *_RFL_ORT.nc (-5), *_rfl_*_img (NG), "
            "*_corr_*_img (Classic)",
    patterns=(r"AV3\d{8}t\d{6}.*_RFL_ORT",
              r"AV5\d{8}t\d{6}_\d{3}.*_RFL_ORT\.nc$",
              r"ang\d{8}t\d{6}.*_rfl_.*",
              r"f\d{6}t\d{2}p\d{2}r\d{2}.*(corr|refl|rfl).*"),
    note="surface reflectance, unitless; OBS siblings picked up automatically",
))
register(Entry(
    sensor="AVIRIS", level="L1B", loader=_aviris,
    expects="the radiance cube, its .hdr, or the folder holding it - "
            "*_RDN_ORT (AVIRIS-3), *_rdn_*_img (NG), *_sc01_ort_img (Classic)",
    patterns=(r"AV3\d{8}t\d{6}.*_RDN_ORT",
              r"AV5\d{8}t\d{6}_\d{3}.*_L1B_RDN_.*_RDN\.nc$",
              r"ang\d{8}t\d{6}.*_rdn_.*",
              r"f\d{6}t\d{2}p\d{2}r\d{2}.*rdn.*"),
    note="at-sensor radiance in uW nm-1 cm-2 sr-1; Classic is scaled int16 "
         "and is divided by its .gain sidecar on read",
))

for _sensor, _levels, _note in [
    ("AVIRIS-CLASSIC", ("L1B", "L2A"), "1987-2021, 224 bands 366-2497 nm, 4-20 m"),
    ("AVIRIS-NG", ("L1B", "L2A"), "2014-, 425 bands 377-2500 nm, 3-8 m"),
    ("AVIRIS3", ("L1B", "L2A"), "2023-, 284 bands 390-2493 nm, ~3 m"),
    ("AVIRIS5", ("L1B", "L2A"),
     "2025-, 424 bands 382-2500 nm; NetCDF. L1B radiance is a separate ORNL "
     "DAAC collection and arrives on the sensor grid"),
]:
    for _lvl in _levels:
        register(Entry(sensor=_sensor, level=_lvl, loader=_aviris,
                       expects=f"{_sensor} {_lvl} cube, .hdr, or folder",
                       note=_note))


register(Entry(
    sensor="NEON", level="L1", loader=_neon,
    expects="NEON_D??_SITE_DP1_YYYYMMDD_HHMMSS_reflectance.h5  (one flightline)",
    patterns=(r"NEON_D\d{2}_[A-Z0-9]{4}_DP1_\d{8}_\d{6}_reflectance\.h5$",),
    note="DP1.30006.001: ATCOR reflectance, 426 bands, 1 m north-up UTM; "
         "slope/aspect/DEM/cos_i/angles from the Metadata tree",
))


# --- planned: reader not written yet -------------------------------------

for _e in [
    Entry("NEON", "L3", None, "NEON_D*_SITE_DP3_*_reflectance.h5  (1 km mosaic tiles)",
          (r"NEON_.*_DP3_.*\.h5$", r"NEON_.*DP3\.30006\.001.*\.h5$"),
          "DP3.30006.001 mosaics: Data_Selection_Index + per-line solar logs, not yet handled"),
]:
    register(_e)


# --- lookup --------------------------------------------------------------


def sniff(path: str | Path) -> tuple[str, str] | None:
    """Guess ``(sensor, level)`` from a filename. None if nothing matches."""
    name = Path(path).name
    for key, entry in REGISTRY.items():
        if entry.matches(name):
            return key
    return None


def resolve(path: str | Path, sensor: str | None, level: str | None) -> Entry:
    """Find the Entry for an explicit sensor/level, or work it out from ``path``."""
    if sensor is None or level is None:
        guess = sniff(path)
        if guess is None:
            raise ValueError(
                f"Cannot tell what {Path(path).name!r} is. Pass sensor= and level= "
                f"explicitly, e.g. hyperproc.open(path, sensor='EMIT', level='L2A'). "
                f"{summary()}"
            )
        sensor = sensor or guess[0]
        level = level or guess[1]

    key = (sensor.upper(), level.upper())
    if key not in REGISTRY:
        known = sorted({s for s, _ in REGISTRY})
        levels = sorted(lv for s, lv in REGISTRY if s == sensor.upper())
        if levels:
            raise ValueError(
                f"No reader for {sensor.upper()} {level.upper()}. "
                f"Known levels for {sensor.upper()}: {', '.join(levels)}"
            )
        raise ValueError(f"Unknown sensor {sensor!r}. Known: {', '.join(known)}")

    entry = REGISTRY[key]
    if not entry.implemented:
        raise NotImplementedError(
            f"{entry.sensor} {entry.level} is registered but its reader is not written yet.\n"
            f"  expects: {entry.expects}\n"
            + (f"  note:    {entry.note}\n" if entry.note else "")
            + f"  to add:  write hyperproc/readers/{entry.sensor.lower()}.py, then set "
              f"loader= in hyperproc/registry.py"
        )
    return entry


def summary() -> str:
    done = sorted(f"{s} {lv}" for (s, lv), e in REGISTRY.items() if e.implemented)
    todo = sorted({s for (s, _), e in REGISTRY.items() if not e.implemented})
    return f"Implemented: {', '.join(done)}. Planned: {', '.join(todo)}."


def list_readers() -> None:
    """Print the dispatch table."""
    print(f"\n  {'sensor':<8} {'level':<6} {'status':<14} expects")
    print("  " + "-" * 76)
    for (s, lv), e in sorted(REGISTRY.items()):
        status = "ready" if e.implemented else "not written"
        print(f"  {s:<8} {lv:<6} {status:<14} {e.expects}")
    print()
