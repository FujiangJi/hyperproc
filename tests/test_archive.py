"""Searching the archives, without touching the network.

A test that calls CMR fails when someone else's server has a bad day, so the
network is mocked: three real responses are recorded in
``tests/data/archive_fixtures/`` and replayed. What is under test is the part
hyperproc owns - the collection table, the query it builds, how a CMR record
becomes a :class:`Granule`, and what it says when it cannot help.

Refresh the fixtures with ``tests/tools/make_archive_fixtures.py`` if CMR's
schema moves; the ``network`` tests below check whether it has.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from hyperproc.archive import COLLECTIONS, ELSEWHERE, describe, resolve
from hyperproc.archive.cmr import Granule, Results, _bbox_of, _granule, _time_of, search

FIXTURES = Path(__file__).resolve().parent / "data" / "archive_fixtures"


class _FakeGranule(dict):
    """Stands in for earthaccess.DataGranule: a dict with .size and .data_links()."""

    def __init__(self, rec):
        super().__init__(umm=rec["umm"])
        self.size = rec["size"]
        self._links = rec["links"]

    def data_links(self):
        return self._links


def _load(name):
    path = FIXTURES / f"{name}.json"
    if not path.is_file():
        pytest.skip(f"no recorded response at {path}")
    return [_FakeGranule(r) for r in json.loads(path.read_text())]


@pytest.fixture
def fake_cmr(monkeypatch):
    """Replay a recorded response, and capture the query that asked for it."""
    seen = {}

    def factory(name):
        import hyperproc.archive.cmr as mod

        class _EA:
            @staticmethod
            def search_data(count=-1, **kwargs):
                seen.update(kwargs)
                seen["count"] = count
                return _load(name)

        monkeypatch.setattr(mod, "_earthaccess", lambda: _EA)
        return seen

    return factory


# --------------------------------------------------------------------------- #
# the collection table                                                         #
# --------------------------------------------------------------------------- #

def test_every_searchable_pair_is_one_the_readers_can_open():
    """COLLECTIONS and REGISTRY are both keyed by (sensor, level), so they can be
    compared directly: anything searchable must also be readable, or the search
    hands back a granule nothing in the package can open.

    Registered is not enough - NEON L3 is registered and not written - so the
    test asks for an implemented reader."""
    import hyperproc as hp
    readable = {(s.upper().replace("-", ""), lv.upper())
                for (s, lv), e in hp.REGISTRY.items() if e.implemented}
    for sensor, level in COLLECTIONS:
        key = (sensor.upper().replace("-", ""), level.upper())
        assert key in readable, (
            f"{sensor} {level} can be searched but no reader opens it; "
            f"readable: {sorted(readable)}")


def test_every_backend_named_in_the_table_exists():
    from hyperproc.archive import api
    for (sensor, level), coll in COLLECTIONS.items():
        assert coll.backend in api._BACKEND, f"{sensor} {level} names no backend"
        assert coll.backend in api._DOWNLOAD_ARGS


def test_search_goes_to_the_archive_that_publishes_the_sensor(monkeypatch):
    """One hp.search over three archives: the table decides, not the caller."""
    from hyperproc.archive import api
    went = []
    for name, mod in api._BACKEND.items():
        monkeypatch.setattr(mod, "search",
                            lambda s, lv, _n=name, **kw: went.append((_n, s, lv)))
    for sensor, level, expected in [("EMIT", "L2A", "cmr"), ("NEON", "L1", "neon"),
                                    ("ENMAP", "L2A", "dlr"), ("DESIS", "L2A", "dlr"),
                                    ("aviris3", "L1B", "cmr")]:
        api.search(sensor, level)
        assert went[-1][0] == expected, f"{sensor} {level} went to {went[-1][0]}"


def test_a_mixed_result_set_is_split_between_its_archives(monkeypatch, tmp_path):
    from hyperproc.archive import api
    from hyperproc.archive.results import Granule
    seen = {}

    def record(part, out, _n, **kw):
        seen[_n] = len(part)
        return []

    for name, mod in api._BACKEND.items():
        monkeypatch.setattr(mod, "download",
                            lambda part, out, _n=name, **kw: record(part, out, _n, **kw))

    def g(sensor, level):
        return Granule(name=f"{sensor}-x", sensor=sensor, level=level, collection="c",
                       version=None, time=None, bbox=None, size_mb=None, cloud=None)

    api.download([g("EMIT", "L2A"), g("ENMAP", "L2A"), g("DESIS", "L2A"),
                  g("NEON", "L1")], tmp_path, verbose=False)
    assert seen == {"cmr": 1, "dlr": 2, "neon": 1}


def test_a_credential_meant_for_another_archive_is_named_not_ignored(monkeypatch, tmp_path):
    from hyperproc.archive import api
    from hyperproc.archive.results import Granule
    monkeypatch.setattr(api.cmr, "download", lambda *a, **k: [])
    emit = Granule(name="e", sensor="EMIT", level="L2A", collection="c", version=None,
                   time=None, bbox=None, size_mb=None, cloud=None)
    with pytest.raises(TypeError, match="token"):
        api.download([emit], tmp_path, token="a-neon-token", verbose=False)


def test_files_is_a_no_op_for_the_archives_where_a_granule_is_its_files():
    from hyperproc.archive import files
    from hyperproc.archive.results import Granule, Results
    emit = Results([Granule(name="e", sensor="EMIT", level="L2A", collection="c",
                            version=None, time=None, bbox=None, size_mb=1.0,
                            cloud=None, links=["https://x/e"])])
    assert files(emit) is emit


def test_files_refuses_to_mix_a_neon_delivery_with_anything_else():
    from hyperproc.archive import files
    from hyperproc.archive.results import Granule
    def g(sensor, level):
        return Granule(name=sensor, sensor=sensor, level=level, collection="c",
                       version=None, time=None, bbox=None, size_mb=None, cloud=None)
    with pytest.raises(ValueError, match="on their own"):
        files([g("NEON", "L1"), g("EMIT", "L2A")])


def test_the_sensors_we_cannot_search_are_named_and_explained():
    """An empty result is worse than a refusal that gives the address."""
    for sensor, why in ELSEWHERE.items():
        assert len(why) > 40, f"{sensor} has no real explanation"
        assert "http" in why, f"{sensor} does not say where to go instead"


@pytest.mark.parametrize("given,expected", [
    ("EMIT", "EMIT"), ("emit", "EMIT"),
    ("AVIRIS-3", "AVIRIS-3"), ("AVIRIS3", "AVIRIS-3"), ("aviris3", "AVIRIS-3"),
    ("AVIRIS_5", "AVIRIS-5"), ("aviris5", "AVIRIS-5"),
    ("PACE", "PACE"), ("oci", "PACE"),
])
def test_resolve_accepts_the_spellings_the_readers_produce(given, expected):
    assert resolve(given, "L1B" if expected != "PACE" else "L1B")[0] == expected


def test_a_sensor_we_cannot_search_says_where_to_go():
    with pytest.raises(ValueError, match="prisma.asi.it"):
        resolve("PRISMA")


def test_an_unknown_sensor_lists_what_is_available():
    with pytest.raises(ValueError, match="searchable"):
        resolve("HYPERION")


def test_a_sensor_with_two_levels_insists_on_one():
    with pytest.raises(ValueError, match="more than one searchable level"):
        resolve("EMIT")


def test_an_impossible_level_lists_the_possible_ones():
    with pytest.raises(ValueError, match=r"try one of \['L1B', 'L2A'\]"):
        resolve("EMIT", "L3")


def test_describe_covers_both_halves():
    text = describe()
    for sensor, _ in COLLECTIONS:
        assert sensor in text
    for sensor in ELSEWHERE:
        assert sensor in text


# --------------------------------------------------------------------------- #
# the query we build                                                           #
# --------------------------------------------------------------------------- #

def test_the_query_carries_the_collection_and_the_filters(fake_cmr):
    seen = fake_cmr("emit_l2a")
    search("EMIT", "L2A", bbox=(-121.0, 34.0, -119.8, 35.1),
           date=("2023-04-20", "2023-04-25"), verbose=False)
    assert seen["short_name"] == "EMITL2ARFL"
    assert seen["bounding_box"] == (-121.0, 34.0, -119.8, 35.1)
    assert seen["temporal"] == ("2023-04-20", "2023-04-25")


def test_version_is_left_open_unless_asked(fake_cmr):
    """EMIT carries two live versions; pinning one would hide 249,428 granules."""
    seen = fake_cmr("emit_l2a")
    search("EMIT", "L2A", verbose=False)
    assert "version" not in seen
    seen.clear()
    search("EMIT", "L2A", version="002", verbose=False)
    assert seen["version"] == "002"


def test_a_single_date_means_that_one_day(fake_cmr):
    seen = fake_cmr("emit_l2a")
    search("EMIT", "L2A", date="2023-04-22", verbose=False)
    assert seen["temporal"] == ("2023-04-22", "2023-04-22")


@pytest.mark.parametrize("bad,match", [
    ((-200, 34, -119, 35), "out of range"),
    ((-121, -100, -119, 35), "out of range"),
    ((-119, 34, -121, 35), "inside out"),
    ((-121, 35, -119, 34), "inside out"),
])
def test_a_broken_bbox_is_refused_before_the_network(fake_cmr, bad, match):
    fake_cmr("emit_l2a")
    with pytest.raises(ValueError, match=match):
        search("EMIT", "L2A", bbox=bad, verbose=False)


# --------------------------------------------------------------------------- #
# turning a CMR record into something usable                                   #
# --------------------------------------------------------------------------- #

def test_a_result_carries_what_a_person_chooses_on(fake_cmr):
    fake_cmr("emit_l2a")
    hits = search("EMIT", "L2A", verbose=False)
    assert len(hits) == 3
    g = hits[0]
    assert isinstance(g, Granule)
    assert g.name.startswith("EMIT_L2A_RFL")
    assert g.sensor == "EMIT" and g.level == "L2A"
    assert g.collection == "EMITL2ARFL"
    assert isinstance(g.time, datetime) and g.time.year == 2023
    assert g.size_mb > 0 and g.size_gb == pytest.approx(g.size_mb / 1024)
    assert 0 <= g.cloud <= 100


def test_the_links_include_the_siblings_the_reader_needs(fake_cmr):
    """EMIT L2A is three files; hp.open finds MASK and RFLUNCERT beside the cube."""
    fake_cmr("emit_l2a")
    g = search("EMIT", "L2A", verbose=False)[0]
    names = [l.rsplit("/", 1)[-1] for l in g.links]
    assert any("_RFL_" in n for n in names)
    assert any("_MASK_" in n for n in names)


def test_the_footprint_comes_back_as_a_box(fake_cmr):
    fake_cmr("emit_l2a")
    g = search("EMIT", "L2A", verbose=False)[0]
    w, s, e, n = g.bbox
    assert w < e and s < n
    assert -180 <= w <= 180 and -90 <= s <= 90


def test_a_polygon_footprint_becomes_its_bounds():
    umm = {"SpatialExtent": {"HorizontalSpatialDomain": {"Geometry": {"GPolygons": [
        {"Boundary": {"Points": [
            {"Longitude": -121.0, "Latitude": 34.0}, {"Longitude": -119.0, "Latitude": 34.5},
            {"Longitude": -119.5, "Latitude": 36.0}, {"Longitude": -121.5, "Latitude": 35.5}]}}]}}}}
    assert _bbox_of(umm) == (-121.5, 34.0, -119.0, 36.0)


def test_a_rectangle_footprint_is_taken_as_given():
    umm = {"SpatialExtent": {"HorizontalSpatialDomain": {"Geometry": {"BoundingRectangles": [
        {"WestBoundingCoordinate": -10.0, "SouthBoundingCoordinate": -5.0,
         "EastBoundingCoordinate": 10.0, "NorthBoundingCoordinate": 5.0}]}}}}
    assert _bbox_of(umm) == (-10.0, -5.0, 10.0, 5.0)


def test_a_granule_without_a_footprint_says_none():
    assert _bbox_of({"SpatialExtent": {"HorizontalSpatialDomain": {"Geometry": {}}}}) is None


@pytest.mark.parametrize("raw", [
    "2023-04-22T19:59:24Z", "2023-04-22T19:59:24.000Z", "2023-04-22T19:59:24+00:00",
])
def test_times_come_back_naive_utc(raw):
    dt = _time_of({"TemporalExtent": {"RangeDateTime": {"BeginningDateTime": raw}}})
    assert (dt.year, dt.month, dt.day, dt.hour) == (2023, 4, 22, 19)
    assert dt.tzinfo is None


def test_a_single_datetime_is_accepted_too():
    dt = _time_of({"TemporalExtent": {"SingleDateTime": "2023-04-22T19:59:24Z"}})
    assert dt.day == 22


# --------------------------------------------------------------------------- #
# the Results container                                                        #
# --------------------------------------------------------------------------- #

def test_results_behave_like_a_sequence(fake_cmr):
    fake_cmr("emit_l2a")
    hits = search("EMIT", "L2A", verbose=False)
    assert len(hits) == 3
    assert isinstance(hits[:2], Results) and len(hits[:2]) == 2
    assert [g.name for g in hits] == [g.name for g in list(hits)]


def test_the_total_size_is_the_sum(fake_cmr):
    fake_cmr("emit_l2a")
    hits = search("EMIT", "L2A", verbose=False)
    assert hits.size_gb == pytest.approx(sum(g.size_mb for g in hits) / 1024)
    assert "GB" in repr(hits)


def test_the_table_is_readable_and_totals(fake_cmr):
    fake_cmr("emit_l2a")
    table = search("EMIT", "L2A", verbose=False).table()
    assert "granule" in table and "3 granules" in table


def test_an_empty_result_says_what_was_asked():
    empty = Results([], {"short_name": "EMITL2ARFL", "temporal": ("2023-01-01", "2023-01-02")})
    assert "no granules" in empty.table()
    assert "EMITL2ARFL" in empty.table()


def test_other_sensors_replay_too(fake_cmr):
    fake_cmr("pace_l2")
    pace = search("PACE", "L2", verbose=False)
    assert len(pace) and pace[0].sensor == "PACE"
    fake_cmr("aviris3_l1b")
    av3 = search("AVIRIS-3", "L1B", verbose=False)
    assert len(av3) and av3[0].collection == "AV3_L1B_RDN_2356"


def test_aviris_reports_no_cloud_and_we_do_not_invent_one(fake_cmr):
    fake_cmr("aviris3_l1b")
    assert all(g.cloud is None for g in search("AVIRIS-3", "L1B", verbose=False))


def test_a_cloud_filter_that_can_only_match_nothing_is_refused(fake_cmr):
    """Silently returning zero rows is how a working search looks broken."""
    seen = fake_cmr("aviris3_l1b")
    with pytest.raises(ValueError, match="does not report cloud cover"):
        search("AVIRIS-3", "L1B", cloud=(0, 10), verbose=False)
    assert seen == {}, "refused before asking CMR anything"


def test_whether_a_cloud_fraction_exists_is_a_property_of_the_collection(fake_cmr):
    """Not of the sensor: PACE publishes one at L2 and none at L1B, measured
    against CMR. A per-sensor rule would get PACE wrong either way round."""
    assert COLLECTIONS[("PACE", "L2")].cloud is True
    assert COLLECTIONS[("PACE", "L1B")].cloud is False
    fake_cmr("pace_l2")
    search("PACE", "L2", cloud=(0, 60), verbose=False)          # fine
    with pytest.raises(ValueError, match="PACE_OCI_L1B_SCI"):
        search("PACE", "L1B", cloud=(0, 60), verbose=False)


def test_the_table_and_the_granules_agree_about_cloud(fake_cmr):
    """The flag says what the fixtures show, so it cannot drift from the archive."""
    for name, pair in [("emit_l2a", ("EMIT", "L2A")), ("pace_l2", ("PACE", "L2")),
                       ("aviris3_l1b", ("AVIRIS-3", "L1B"))]:
        fake_cmr(name)
        got = search(*pair, verbose=False)
        reported = any(g.cloud is not None for g in got)
        assert reported == COLLECTIONS[pair].cloud, f"{pair} disagrees with its fixture"


# --------------------------------------------------------------------------- #
# against the live archive - deselected by default                             #
# --------------------------------------------------------------------------- #

@pytest.mark.network
def test_cmr_still_answers_the_way_the_fixtures_say():
    """Run with -m network to check the recorded responses have not gone stale."""
    hits = search("EMIT", "L2A", bbox=(-121.0, 34.0, -119.8, 35.1),
                  date=("2023-04-20", "2023-04-25"), verbose=False)
    assert len(hits) >= 1
    assert any("20230422T195924" in g.name for g in hits)


# --------------------------------------------------------------------------- #
# what this process could actually download                                    #
# --------------------------------------------------------------------------- #

def test_the_two_dlr_missions_are_reported_separately(monkeypatch):
    """DLR grants EnMAP and DESIS to different accounts. One flag for "DLR"
    reads found when you hold only one of them, and then waves the other
    through to a refusal at download time - which is exactly what happened."""
    from hyperproc.archive import credentials
    for v in ("EARTHDATA_USERNAME", "EARTHDATA_TOKEN", "NEON_TOKEN",
              "DLR_EOC_USERNAME", "DLR_EOC_PASSWORD",
              "ENMAP_USERNAME", "ENMAP_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr("netrc.netrc", lambda *a: (_ for _ in ()).throw(FileNotFoundError))
    monkeypatch.setenv("DESIS_USERNAME", "d")
    monkeypatch.setenv("DESIS_PASSWORD", "dp")

    got = credentials()
    assert got["DESIS"] is True
    assert got["ENMAP"] is False, "holding DESIS must not claim EnMAP"
    assert got["cmr"] is False and got["neon"] is False


def test_can_download_asks_the_question_download_would_answer_by_failing(monkeypatch):
    from hyperproc.archive import can_download
    monkeypatch.setattr("hyperproc.archive.api.credentials",
                        lambda: {"cmr": True, "neon": False,
                                 "ENMAP": False, "DESIS": True})
    assert can_download("EMIT", "L2A") is True
    assert can_download("PACE", "L2") is True
    assert can_download("NEON", "L1") is False
    assert can_download("DESIS", "L2A") is True
    assert can_download("ENMAP", "L2A") is False, "the case that misled the notebook"


def test_a_shared_dlr_account_covers_both_missions(monkeypatch):
    from hyperproc.archive import credentials
    for v in ("ENMAP_USERNAME", "ENMAP_PASSWORD", "DESIS_USERNAME", "DESIS_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr("netrc.netrc", lambda *a: (_ for _ in ()).throw(FileNotFoundError))
    monkeypatch.setenv("DLR_EOC_USERNAME", "both")
    monkeypatch.setenv("DLR_EOC_PASSWORD", "pw")
    got = credentials()
    assert got["ENMAP"] is True and got["DESIS"] is True


def test_credentials_never_returns_a_secret(monkeypatch):
    from hyperproc.archive import credentials
    monkeypatch.setenv("DESIS_USERNAME", "a-real-username")
    monkeypatch.setenv("DESIS_PASSWORD", "a-real-password")
    got = credentials()
    assert all(isinstance(v, bool) for v in got.values())
    assert "a-real-username" not in repr(got) and "a-real-password" not in repr(got)


# --------------------------------------------------------------------------- #
# packaging                                                                    #
# --------------------------------------------------------------------------- #

def test_every_subpackage_would_be_shipped():
    """hyperproc.archive was written, tested, documented - and left out of the
    wheel, because pyproject listed packages by hand and nobody remembered to
    add it. Discovery fixes that; this notices if it is ever listed by hand
    again and the list falls behind the source tree."""
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    on_disk = {"hyperproc"} | {
        f"hyperproc.{p.relative_to(root / 'hyperproc').as_posix().replace('/', '.')}"
        for p in (root / "hyperproc").rglob("__init__.py")
        if p.parent != root / "hyperproc"
        for p in [p.parent]
    }
    cfg = tomllib.loads((root / "pyproject.toml").read_text()).get("tool", {}).get("setuptools", {})

    listed = cfg.get("packages")
    if isinstance(listed, list):
        missing = on_disk - set(listed)
        assert not missing, f"not in pyproject's packages list, so not in the wheel: {sorted(missing)}"
    else:
        patterns = (cfg.get("packages", {}).get("find", {}) or {}).get("include", [])
        assert patterns, "no explicit list and no find.include: nothing would be packaged"
        assert any(p in ("hyperproc*", "hyperproc.*", "*") for p in patterns), \
            f"find.include={patterns} may not cover every subpackage"
