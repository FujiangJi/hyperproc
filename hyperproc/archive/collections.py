"""Which archives hyperproc can search, and which it cannot.

The table below is the whole of the module's knowledge: it maps the
``(sensor, level)`` names the readers already use onto a collection in one of
three archives, so a search result can be handed straight to
:func:`hyperproc.open`.

=========  ==============================  =====================  ==============
backend    archive                         searching              downloading
=========  ==============================  =====================  ==============
``cmr``    NASA Common Metadata Repository anonymous              Earthdata login
``neon``   NEON Data API v0                anonymous              NEON API token
``dlr``    DLR EOC Geoservice STAC         anonymous              EOC account
=========  ==============================  =====================  ==============

Every count in the comments was measured against the archive, not assumed.

**Versions are deliberately not pinned.** EMIT carries two live versions -
249,428 granules at v001 and 23,267 at v002 for the L1B radiance - so pinning
the newest would silently hide nine tenths of the archive. Pass ``version=``
to :func:`hyperproc.search` when you want one.
"""
from __future__ import annotations

import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class Collection:
    """One searchable archive entry.

    Attributes:
        short_name: the collection id in its own archive - a CMR ``ShortName``,
            a NEON product code, a STAC collection id.
        what: the product, in the provider's words.
        granules: granules in the archive when this table was written, as a
            rough guide to what a broad search will return.
        backend: which of ``"cmr"``, ``"neon"``, ``"dlr"`` answers the query.
        cloud: whether the provider publishes a cloud fraction for this
            collection. Measured, not assumed, and not a property of the
            sensor: PACE reports one at L2 and none at L1B. A ``cloud=``
            filter on a collection that reports none can only ever match
            nothing, so :func:`hyperproc.search` refuses it.
        siblings: the extra files a granule carries. hyperproc's readers find
            these themselves once they are beside the main file, so the
            download brings what :func:`hyperproc.open` needs.
    """
    short_name: str
    what: str
    granules: int
    backend: str = "cmr"
    cloud: bool = True
    siblings: tuple[str, ...] = ()
    #: shown when a search of this collection comes back empty, where the
    #: reason is a property of the archive rather than of the query
    note: str = ""


#: ``(sensor, level)`` -> collection. Keys match the reader names.
COLLECTIONS: dict[tuple[str, str], Collection] = {
    # --- NASA CMR, over earthaccess ---------------------------------------
    ("EMIT", "L1B"): Collection(
        "EMITL1BRAD", "at-sensor calibrated radiance and geolocation", 272_695,
        siblings=("OBS", "GLT")),
    ("EMIT", "L2A"): Collection(
        "EMITL2ARFL", "surface reflectance and uncertainty, 60 m", 272_629,
        siblings=("MASK", "RFLUNCERT")),

    ("PACE", "L1B"): Collection(
        "PACE_OCI_L1B_SCI", "OCI Level-1B science data", 226_558, cloud=False),
    ("PACE", "L2"): Collection(
        "PACE_OCI_L2_SFREFL", "OCI Level-2 regional surface reflectance", 125_020),

    ("AVIRIS-3", "L1B"): Collection(
        "AV3_L1B_RDN_2356", "AVIRIS-3 calibrated radiance", 21_501, cloud=False),
    ("AVIRIS-3", "L2A"): Collection(
        "AV3_L2A_RFL_2357", "AVIRIS-3 orthocorrected surface reflectance", 511,
        cloud=False, note=("AVIRIS-3 reflectance is published for only a small share of flights "
              "- 511 granules against 21,501 of radiance - so an empty result here "
              "usually means the flight was never reflectance-processed, not that "
              "nothing was flown. Search level='L1B' to see whether radiance exists, "
              "and run hyperproc.atmos.process on it yourself.")),

    ("AVIRIS-5", "L1B"): Collection(
        "AV5_L1B_RDN_2483", "AVIRIS-5 calibrated radiance", 5_811, cloud=False),
    ("AVIRIS-5", "L2A"): Collection(
        "AV5_L2A_RFL_2484", "AVIRIS-5 orthocorrected surface reflectance", 5_776, cloud=False),

    # --- NEON Data API ----------------------------------------------------
    # One entry is a site-month delivery holding every flightline flown that
    # month, not a single file; hyperproc.archive.files() opens it up.
    ("NEON", "L1"): Collection(
        "DP1.30006.001", "AOP flightline directional reflectance, 1 m", 378,
        backend="neon", cloud=False,
        note=("NEON publishes one delivery per site and month - 378 of them over "
              "59 sites, 2013 to 2026 - each holding every flightline flown. "
              "hyperproc.archive.files() lists the flightlines inside one, which "
              "needs a NEON API token.")),

    # --- DLR EOC Geoservice STAC -----------------------------------------
    ("ENMAP", "L1B"): Collection(
        "ENMAP_HSI_L1B", "EnMAP at-sensor radiance, VNIR and SWIR unmerged", 238_501,
        backend="dlr", siblings=("METADATA.XML", "QL_QUALITY_*")),
    ("ENMAP", "L1C"): Collection(
        "ENMAP_HSI_L1C", "EnMAP orthorectified at-sensor radiance", 206_404,
        backend="dlr", siblings=("METADATA.XML", "QL_QUALITY_*")),
    ("ENMAP", "L2A"): Collection(
        "ENMAP_HSI_L2A", "EnMAP surface reflectance, land or water", 238_494,
        backend="dlr", siblings=("METADATA.XML", "QL_QUALITY_*")),

    ("DESIS", "L2A"): Collection(
        "DESIS_HSI_L2A", "DESIS surface reflectance from the ISS", 14_958,
        backend="dlr", siblings=("METADATA.xml", "QL_QUALITY*")),
}

#: Spellings the readers produce, mapped onto the keys above.
ALIASES = {
    "AVIRIS3": "AVIRIS-3", "AVIRIS_3": "AVIRIS-3",
    "AVIRIS5": "AVIRIS-5", "AVIRIS_5": "AVIRIS-5",
    "OCI": "PACE",
}

#: Levels a reader opens but no archive here publishes. Without these, asking
#: for one gets the bare "try one of [...]", which does not say why.
LEVEL_NOTES = {
    ("NEON", "L3"): (
        "NEON DP3.30006.001 mosaic tiles exist, but hyperproc's reader handles "
        "flightlines (DP1) only; search level='L1'."),
    ("DESIS", "L1B"): (
        "DLR publishes only DESIS L2A openly; L1B and L1C are ordered through "
        "Teledyne Brown at https://www.teledyneimaging.com/en/products/"
        "product-details/desis/ . hyperproc.open reads them once you have them."),
    ("DESIS", "L1C"): (
        "DLR publishes only DESIS L2A openly; L1B and L1C are ordered through "
        "Teledyne Brown at https://www.teledyneimaging.com/en/products/"
        "product-details/desis/ . hyperproc.open reads them once you have them."),
}

#: Sensors hyperproc reads but cannot search, and where to get them instead.
#: Saying so is the point: a search that quietly returns nothing is worse than
#: one that explains itself.
ELSEWHERE = {
    "PRISMA": (
        "ASI runs no public search API; register and order scenes at "
        "https://prisma.asi.it/. hyperproc.open reads the .he5 files it "
        "gives you."),
    "TANAGER": (
        "Planet distributes Tanager commercially through its own API, "
        "https://developers.planet.com/. Free sample products are published "
        "as an open STAC catalogue at "
        "https://www.planet.com/data/stac/tanager-core-imagery/catalog.json - "
        "a static catalogue of nine themed collections, so it is browsed "
        "rather than queried. hyperproc.open reads the ortho HDF5 products "
        "from either route."),
    "AVIRIS-NG": (
        "Only campaign subsets (ABoVE, SHIFT and others) are in CMR; the full "
        "archive is browsed and ordered at "
        "https://aviris.jpl.nasa.gov/dataportal/, the same portal as the "
        "classic archive."),
    "AVIRIS-CLASSIC": (
        "The classic archive is browsed and ordered at "
        "https://aviris.jpl.nasa.gov/dataportal/"),
}


def resolve(sensor: str, level: str | None = None) -> tuple[str, str, Collection]:
    """``(sensor, level, collection)`` for a request, or a ValueError saying why not."""
    key = str(sensor).upper().replace(" ", "")
    key = ALIASES.get(key.replace("-", "").replace("_", ""), ALIASES.get(key, key))
    if key not in {s for s, _ in COLLECTIONS}:
        if key in ELSEWHERE:
            raise ValueError(f"hyperproc cannot search {key}. {ELSEWHERE[key]}")
        known = sorted({s for s, _ in COLLECTIONS})
        raise ValueError(f"unknown sensor {sensor!r}; searchable: {known}")

    levels = [lv for s, lv in COLLECTIONS if s == key]
    if level is None:
        if len(levels) > 1:
            raise ValueError(
                f"{key} has more than one searchable level {sorted(levels)}; pass level=")
        level = levels[0]
    lv = str(level).upper()
    if (key, lv) not in COLLECTIONS:
        why = LEVEL_NOTES.get((key, lv))
        raise ValueError(f"{key} has no level {level!r}; try one of {sorted(levels)}"
                         + (f". {why}" if why else ""))
    return key, lv, COLLECTIONS[(key, lv)]


#: What each backend needs before it will hand over bytes, quoted in errors.
BACKENDS = {
    "cmr": ("NASA CMR", "a free Earthdata login (https://urs.earthdata.nasa.gov)"),
    "neon": ("NEON Data API", "a NEON API token (https://data.neonscience.org/myaccount)"),
    # One sign-on, but access is granted per mission through two front doors,
    # so the two accounts need not be the same one.
    "dlr": ("DLR EOC Geoservice",
            "a free account per mission - EnMAP at https://www.enmap.org/data_access/ , "
            "DESIS through EOWEB at https://eoweb.dlr.de/egp/"),
}


def describe() -> str:
    """A table of what can be searched and what cannot."""
    rows = ["sensor        level  collection            granules  product",
            "-" * 92]
    last = None
    for (s, lv), c in sorted(COLLECTIONS.items(), key=lambda kv: (kv[1].backend, kv[0])):
        if c.backend != last:
            last = c.backend
            who, need = BACKENDS[c.backend]
            rows.append(f"[{who}]  search anonymous, download needs {need}")
        rows.append(f"{s:13s} {lv:6s} {c.short_name:21s} {c.granules:9,d}  {c.what}")
    if LEVEL_NOTES:
        rows += ["", "levels the readers open but no archive here publishes:"]
        for (sensor, level), why in sorted(LEVEL_NOTES.items()):
            body = textwrap.wrap(" ".join(why.split()), width=74,
                                 break_long_words=False, break_on_hyphens=False)
            rows.append(f"  {sensor + ' ' + level:15s} {body[0]}")
            rows += [f"  {'':15s} {line}" for line in body[1:]]
            rows.append("")

    rows += ["", "not searchable from here - where to get them instead:"]
    for s, why in sorted(ELSEWHERE.items()):
        # wrapped whole, not cut at the first full stop: the second sentence is
        # often the one with the address you actually need
        body = textwrap.wrap(" ".join(why.split()), width=74,
                             break_long_words=False, break_on_hyphens=False)
        rows.append(f"  {s:15s} {body[0]}")
        rows += [f"  {'':15s} {line}" for line in body[1:]]
        rows.append("")
    return "\n".join(rows).rstrip()
