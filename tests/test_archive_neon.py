"""hyperproc.archive.neon - the NEON Data API backend.

NEON is the odd one out of the three archives: it publishes a site-month at a
time rather than a granule, its search is anonymous but its file listing is
not, and it states a site's coordinates rather than the flight box. Each of
those is a behaviour a user will run into, so each has a test.

The site list is replayed from ``tests/data/archive_fixtures/neon_sites.json``.
The file listing cannot be recorded without a token - NEON began requiring one
in June 2026 - so the one used here is written out below against NEON's
documented shape, and a ``network`` test checks the real thing when a token is
in the environment.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from hyperproc.archive import neon
from hyperproc.archive.results import Granule

FIXTURES = Path(__file__).parent / "data" / "archive_fixtures"

#: NEON's documented ``/data/{product}/{site}/{month}`` payload, kept small.
#: The flightline names are the ones in tests/data/NEON_AOP, so a test that
#: says "these are the files" is saying something checkable.
FILE_LISTING = {
    "productCode": "DP1.30006.001",
    "siteCode": "BART",
    "month": "2019-08",
    "release": "RELEASE-2025",
    "files": [
        {"name": "NEON_D01_BART_DP1_20190825_144302_reflectance.h5",
         "size": 9_162_411_735, "md5": None, "crc32": None,
         "url": "https://neon-aop.example/144302?X-Signature=abc"},
        {"name": "NEON_D01_BART_DP1_20190825_145110_reflectance.h5",
         "size": 9_004_120_411, "md5": None, "crc32": None,
         "url": "https://neon-aop.example/145110?X-Signature=def"},
        {"name": "NEON_D01_BART_2019_reflectance_flightlines.kml",
         "size": 40_112, "md5": None, "crc32": None,
         "url": "https://neon-aop.example/kml?X-Signature=ghi"},
        {"name": "NEON.D01.BART.DP1.30006.001.readme.20250101T000000Z.txt",
         "size": 8_441, "md5": None, "crc32": None,
         "url": "https://neon-aop.example/readme?X-Signature=jkl"},
    ],
}


@pytest.fixture
def fake_neon(monkeypatch):
    """Replay ``/sites`` from the fixture and ``/data/...`` from the listing.

    Returns the list of (path, token) pairs the code asked for, so a test can
    assert on the request as well as on the answer.
    """
    sites = json.loads((FIXTURES / "neon_sites.json").read_text())
    asked: list[tuple[str, str | None]] = []

    def fake_get(path, token=None, **params):
        asked.append((path, token))
        if path == "sites":
            return sites
        if path.startswith("data/"):
            if not token:
                raise PermissionError(f"NEON refused {path}. {neon.NEEDS_TOKEN}")
            return FILE_LISTING
        raise FileNotFoundError(path)              # pragma: no cover - defensive

    monkeypatch.setattr(neon, "_get", fake_get)
    monkeypatch.setattr(neon, "_SITES", None)
    monkeypatch.delenv("NEON_TOKEN", raising=False)
    return asked


# --------------------------------------------------------------------------- #
# searching, which needs no token                                              #
# --------------------------------------------------------------------------- #

def test_a_search_finds_the_site_the_box_covers(fake_neon):
    hits = neon.search("NEON", "L1", bbox=(-71.4, 44.0, -71.2, 44.2), verbose=False)
    assert hits, "BART sits inside this box"
    assert {g.raw["site"] for g in hits} == {"BART"}
    assert all(g.collection == "DP1.30006.001" for g in hits)


def test_searching_never_sends_a_token(fake_neon):
    neon.search("NEON", "L1", site="BART", verbose=False)
    assert [tok for _p, tok in fake_neon] == [None], \
        "the site list is public; sending a token would imply it is not"


def test_a_box_far_from_every_site_comes_back_empty(fake_neon):
    hits = neon.search("NEON", "L1", bbox=(100.0, 10.0, 101.0, 11.0), verbose=False)
    assert len(hits) == 0
    assert "site-month" not in hits.table()
    assert "no granules matched" in hits.table()


def test_the_site_radius_is_a_stated_tolerance_not_a_made_up_footprint(fake_neon):
    """NEON publishes the site's coordinates, not its flight box. A box just
    short of BART matches only because the tolerance says so."""
    near = (-71.6, 44.0, -71.4, 44.2)             # BART is at -71.287, outside this
    assert len(neon.search("NEON", "L1", bbox=near, site_radius_km=0.1, verbose=False)) == 0
    assert len(neon.search("NEON", "L1", bbox=near, site_radius_km=20, verbose=False)) > 0


def test_a_delivery_has_no_size_and_says_so_rather_than_guessing(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", verbose=False)
    assert all(g.size_mb is None for g in hits)
    assert hits.unsized == len(hits)
    assert "size not published" in repr(hits)


def test_the_footprint_is_the_site_point(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", verbose=False)
    w, s, e, n = hits[0].bbox
    assert (w, s) == (e, n), "a point, because NEON publishes no flight box"
    assert -71.3 < w < -71.2 and 44.0 < s < 44.1


def test_months_are_filtered_inclusively(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date=("2019-01", "2019-12"),
                       verbose=False)
    assert [g.raw["month"] for g in hits] == ["2019-08"]


@pytest.mark.parametrize("given,expected", [
    ("2019-08", ("2019-08", "2019-08")),
    ("2019-08-25", ("2019-08", "2019-08")),
    (("2019-06-01", "2019-09-30"), ("2019-06", "2019-09")),
    (("2019-09", "2019-06"), ("2019-06", "2019-09")),      # back to front
])
def test_a_date_is_read_as_the_month_a_delivery_belongs_to(given, expected):
    assert neon._months(given) == expected


def test_a_date_that_is_not_a_date_is_refused():
    with pytest.raises(ValueError, match="YYYY-MM"):
        neon._months("last summer")


def test_results_are_newest_first(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", verbose=False)
    times = [g.time for g in hits]
    assert times == sorted(times, reverse=True)


def test_count_caps_the_result(fake_neon):
    assert len(neon.search("NEON", "L1", site="BART", count=2, verbose=False)) == 2
    assert len(neon.search("NEON", "L1", site="BART", count=-1, verbose=False)) > 2


@pytest.mark.parametrize("bad,match", [
    ((-200, 0, 10, 10), "out of range"),
    ((10, 0, -10, 10), "inside out"),
])
def test_a_broken_bbox_is_refused_before_the_network(fake_neon, bad, match):
    with pytest.raises(ValueError, match=match):
        neon.search("NEON", "L1", bbox=bad, verbose=False)
    assert fake_neon == [], "refused before asking NEON anything"


def test_only_the_spectrometer_product_is_searched(fake_neon):
    """BART's fixture keeps all ~180 of its products; a search must pick one."""
    hits = neon.search("NEON", "L1", site="BART", count=-1, verbose=False)
    assert {g.collection for g in hits} == {"DP1.30006.001"}


# --------------------------------------------------------------------------- #
# listing files, which does need a token                                       #
# --------------------------------------------------------------------------- #

def test_listing_files_without_a_token_says_what_to_do(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    with pytest.raises(PermissionError) as exc:
        neon.files(hits, verbose=False)
    said = str(exc.value)
    assert "June 2026" in said and "NEON_TOKEN" in said
    assert "data.neonscience.org/myaccount" in said


def test_a_missing_token_is_not_a_reason_to_skip_asking(fake_neon):
    """The endpoint is NEON's to open or close. Refusing locally would lock out
    anyone NEON does answer, so the request goes out and the 403 does the
    talking - which is also what makes the error name the real cause."""
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    with pytest.raises(PermissionError):
        neon.files(hits, verbose=False)
    assert ("data/DP1.30006.001/BART/2019-08", None) in fake_neon


def test_an_open_endpoint_would_just_work(fake_neon, monkeypatch):
    """If NEON reopens the endpoint, nothing here needs changing."""
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    # as if NEON answered the data endpoint with no token, the way it did before
    # June 2026; the fixture's own fake refuses without one
    monkeypatch.setattr(neon, "_get", lambda path, token=None, **kw: FILE_LISTING)
    got = neon.files(hits, verbose=False)
    assert len(got) == 2


def test_the_token_comes_from_the_environment_when_not_passed(fake_neon, monkeypatch):
    monkeypatch.setenv("NEON_TOKEN", "from-the-environment")
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    neon.files(hits, verbose=False)
    assert ("data/DP1.30006.001/BART/2019-08", "from-the-environment") in fake_neon


def test_files_keeps_what_the_reader_opens_and_drops_the_paperwork(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    got = neon.files(hits, token="t", verbose=False)
    assert [g.name for g in got] == [
        "NEON_D01_BART_DP1_20190825_144302_reflectance.h5",
        "NEON_D01_BART_DP1_20190825_145110_reflectance.h5",
    ], "the kml and the readme are not granules"


def test_the_default_filter_can_be_turned_off(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    assert len(neon.files(hits, token="t", pattern="*", verbose=False)) == 4
    assert len(neon.files(hits, token="t", pattern="*.kml", verbose=False)) == 1


def test_a_listed_file_is_a_granule_with_a_size_a_time_and_a_link(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    g = neon.files(hits, token="t", verbose=False)[0]
    assert isinstance(g, Granule)
    assert g.size_mb == pytest.approx(9162.4, abs=0.1)
    assert g.time == datetime(2019, 8, 25, 14, 43, 2), "from the flightline's own name"
    assert g.links == ["https://neon-aop.example/144302?X-Signature=abc"]
    assert g.version == "RELEASE-2025"
    assert g.bbox == hits[0].bbox, "the flightline inherits the site's location"


def test_a_file_list_reports_a_real_total(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    got = neon.files(hits, token="t", verbose=False)
    assert got.unsized == 0
    assert got.size_gb == pytest.approx(17.7, abs=0.1)


def test_one_delivery_can_be_passed_on_its_own(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    assert len(neon.files(hits[0], token="t", verbose=False)) == 2


def test_the_name_of_a_delivery_reads_as_the_api_path(fake_neon):
    hits = neon.search("NEON", "L1", site="BART", date="2019-08", verbose=False)
    assert hits[0].name == "DP1.30006.001/BART/2019-08"


@pytest.mark.parametrize("name,when", [
    ("NEON_D01_BART_DP1_20190825_145110_reflectance.h5", datetime(2019, 8, 25, 14, 51, 10)),
    ("NEON.D01.BART.DP1.30006.001.readme.txt", None),
])
def test_a_flightline_time_is_read_from_its_name(name, when):
    assert neon._flight_time(name) == when


# --------------------------------------------------------------------------- #
# the level that exists but is not searchable                                  #
# --------------------------------------------------------------------------- #

def test_asking_for_the_mosaic_tiles_explains_why_not():
    from hyperproc.archive import resolve
    with pytest.raises(ValueError, match="DP3.30006.001"):
        resolve("NEON", "L3")


@pytest.mark.network
def test_neon_still_answers_the_way_the_fixture_says():
    """The site list is public, so this needs no token and no skip."""
    live = {s["siteCode"]: s for s in neon._get("sites")}
    recorded = json.loads((FIXTURES / "neon_sites.json").read_text())
    for rec in recorded:
        now = live[rec["siteCode"]]
        assert now["siteLatitude"] == rec["siteLatitude"]
        assert now["siteLongitude"] == rec["siteLongitude"]
        codes = {d["dataProductCode"] for d in now["dataProducts"]}
        assert "DP1.30006.001" in codes


@pytest.mark.network
def test_the_data_endpoint_really_does_require_a_token():
    """The premise of the two-step design. If NEON reopens the endpoint this
    fails, and the module can go back to one step."""
    import os
    if os.environ.get("NEON_TOKEN"):
        pytest.skip("a token is set, so this cannot observe the anonymous case")
    with pytest.raises(PermissionError, match="June 2026"):
        neon._get("data/DP1.30006.001/BART/2019-08")
