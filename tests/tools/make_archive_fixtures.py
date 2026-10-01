"""Re-record the archive responses that tests/test_archive*.py replay.

Three archives answer hyperproc's searches, and each is recorded here: NASA's
CMR through ``earthaccess``, NEON's Data API, and DLR's EOC STAC catalogue.

Run this only when an archive's schema changes or the fixtures go stale - the
``network``-marked tests are what tell you:

    pytest tests/ -m network

Then read the diff before committing it. A fixture refreshed without reading
the diff asserts whatever the archive says today, which is not a test.

The NEON file listing (``neon_files.json``) needs a token, since NEON began
requiring one in June 2026; set ``NEON_TOKEN`` before running, or that one
fixture is left as it is and everything else is refreshed.
"""
from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "data" / "archive_fixtures"

#: One CMR recording per shape we need: a cloud-reporting sensor, a swath
#: sensor, and an airborne collection that reports no cloud at all.
CMR_CASES = {
    "emit_l2a": dict(short_name="EMITL2ARFL", bounding_box=(-121.0, 34.0, -119.8, 35.1),
                     temporal=("2023-04-20", "2023-04-25")),
    "pace_l2": dict(short_name="PACE_OCI_L2_SFREFL", bounding_box=(-125, 32, -115, 42),
                    temporal=("2026-04-22", "2026-04-23")),
    "aviris3_l1b": dict(short_name="AV3_L1B_RDN_2356", bounding_box=(-114, 37, -109, 42),
                        temporal=("2023-10-01", "2023-10-31")),
}

#: DLR: one EnMAP level (thirteen assets, all in the ``_COG`` spelling) and
#: DESIS (six assets, plainly named). Both around BART and Bavaria so the
#: bbox filtering in the tests has something to bite on.
DLR_CASES = {
    "enmap_l2a": dict(collections=["ENMAP_HSI_L2A"], bbox=[10.0, 47.0, 11.5, 48.5],
                      datetime="2023-06-01T00:00:00Z/2023-09-30T23:59:59Z"),
    "desis_l2a": dict(collections=["DESIS_HSI_L2A"], bbox=[-120.0, 34.0, -118.0, 36.0]),
}

#: NEON: the site list is the whole of an anonymous search, so it is trimmed to
#: the sites the tests name rather than carrying all 81.
NEON_SITES = ("BART", "HARV", "ABBY", "SJER")
NEON_DELIVERY = ("DP1.30006.001", "BART", "2019-08")


def cmr() -> None:
    import earthaccess

    for name, query in CMR_CASES.items():
        granules = earthaccess.search_data(count=3, **query)
        # only the umm block, the size and the links: all our code reads
        records = [{"umm": g["umm"],
                    "size": float(getattr(g, "size", 0.0) or 0.0),
                    "links": list(g.data_links() or [])} for g in granules]
        _write(f"{name}.json", records, f"{len(records)} granules")


def dlr() -> None:
    import requests

    from hyperproc.archive.dlr import BASE

    for name, body in DLR_CASES.items():
        r = requests.post(f"{BASE}/search", json=dict(body, limit=3), timeout=180)
        r.raise_for_status()
        got = r.json()
        # Trimmed to what hyperproc reads, so the fixture stays a size a person
        # will actually read in a diff: 235 KB down to 25 KB. ``links`` are
        # catalogue navigation; ``raster:bands`` and ``eo:bands`` repeat every
        # one of EnMAP's 224 bands inside every one of its 13 assets, and the
        # reader takes wavelengths from the granule's METADATA.XML regardless.
        feats = []
        for f in got["features"]:
            f = {k: v for k, v in f.items() if k != "links"}
            f["assets"] = {k: {kk: vv for kk, vv in a.items()
                               if kk not in ("raster:bands", "eo:bands")}
                           for k, a in f["assets"].items()}
            feats.append(f)
        _write(f"{name}.json",
               {"numberMatched": got.get("numberMatched"), "features": feats},
               f"{len(feats)} of {got.get('numberMatched')} items")


def neon() -> None:
    from hyperproc.archive.neon import _get, token_from

    sites = [s for s in _get("sites") if s["siteCode"] in NEON_SITES]
    # one site keeps its full product list; the rest keep only the spectrometer,
    # because a NEON site carries about 180 products and none of them matter here
    for s in sites:
        if s["siteCode"] != "BART":
            s["dataProducts"] = [d for d in s["dataProducts"]
                                 if d["dataProductCode"].startswith("DP1.30006")]
        # availableDataUrls is one URL per month per product and nothing reads
        # it: the search builds the path itself from product, site and month
        for d in s["dataProducts"]:
            d.pop("availableDataUrls", None)
    _write("neon_sites.json", sites, f"{len(sites)} sites, BART keeping all products")

    token = token_from()
    if not token:
        print("  neon_files      skipped: no NEON_TOKEN, listing files needs one")
        return
    product, site, month = NEON_DELIVERY
    data = _get(f"data/{product}/{site}/{month}", token=token)
    # the signed urls expire within the hour and must not be committed
    data["files"] = [{k: ("<signed>" if k == "url" else v) for k, v in f.items()}
                     for f in data["files"]]
    _write("neon_files.json", data, f"{len(data['files'])} files")


def _write(name: str, payload, what: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=1))
    print(f"  {name:18s} {what:34s} -> {path.stat().st_size / 1024:.0f} KB")


def main() -> int:
    for step in (cmr, neon, dlr):
        print(step.__name__.upper())
        step()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
