"""The parts of ``hyperproc.atmos`` that can be checked without running ISOFIT.

A retrieval takes tens of minutes, needs several GB of radiative-transfer
assets and a granule, so none of that belongs in a test suite. What does belong
is everything around it: the table that decides how each sensor reaches
``apply_oe``, the atmosphere and aerosol choices, the file names ISOFIT parses
back, and the config rewriting. Those are pure functions with answers known in
advance, and they are where a wrong answer is silent - a mis-parsed file id or a
winter atmosphere over a humid scene does not crash, it just gives a worse
retrieval hours later.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from hyperproc.atmos import aerosols
from hyperproc.atmos._runner import apply_overrides
from hyperproc.atmos.correct import (ATMOSPHERES, ENGINES, atmosphere_for, neighbor_cap,
                                     resolve_neighbors)
from hyperproc.atmos.dem import SOURCES, tile_id, tile_url
from hyperproc.atmos.inputs import (SENSORS, SensorSpec, _ALIASES, acquisition_time,
                                    hdr_path, names_for, sensor_spec, write_envi_header)


# --------------------------------------------------------------------------- #
# which MODTRAN atmosphere a scene gets                                        #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("lat,month,expected", [
    (0.0, 1, "ATM_TROPICAL"),          # the tropics have no season here
    (0.0, 7, "ATM_TROPICAL"),
    (23.4, 1, "ATM_TROPICAL"),         # just inside the tropical band
    (-23.4, 7, "ATM_TROPICAL"),
    (23.5, 7, "ATM_MIDLAT_SUMMER"),    # the boundary itself is mid-latitude
    (40.0, 7, "ATM_MIDLAT_SUMMER"),    # northern July
    (40.0, 1, "ATM_MIDLAT_WINTER"),    # northern January
    (-40.0, 7, "ATM_MIDLAT_WINTER"),   # southern July IS winter
    (-40.0, 1, "ATM_MIDLAT_SUMMER"),
    (59.9, 1, "ATM_MIDLAT_WINTER"),
    (60.0, 1, "ATM_SUBARC_WINTER"),    # the boundary itself is sub-arctic
    (70.0, 7, "ATM_SUBARC_SUMMER"),
    (-70.0, 7, "ATM_SUBARC_WINTER"),
])
def test_atmosphere_for_known_cases(lat, month, expected):
    assert atmosphere_for(lat, month) == expected


def test_the_hemispheres_have_opposite_winters():
    """The bug this guards is picking a winter atmosphere for a humid summer scene.

    ISOFIT takes the top of the water-vapour grid from the class - 5.35 g/cm2
    for summer against 1.37 for winter - so getting this backwards rails the
    retrieval rather than failing it.
    """
    for month in (5, 6, 7, 8):
        assert atmosphere_for(45.0, month) == "ATM_MIDLAT_SUMMER"
        assert atmosphere_for(-45.0, month) == "ATM_MIDLAT_WINTER"
    for month in (11, 12, 1, 2):
        assert atmosphere_for(45.0, month) == "ATM_MIDLAT_WINTER"
        assert atmosphere_for(-45.0, month) == "ATM_MIDLAT_SUMMER"


def test_every_atmosphere_returned_is_one_isofit_knows():
    for lat in np.arange(-85.0, 86.0, 5.0):
        for month in range(1, 13):
            assert atmosphere_for(float(lat), month) in ATMOSPHERES


# --------------------------------------------------------------------------- #
# Copernicus DEM tile naming                                                   #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("lat0,lon0,expected", [
    (37, -80, "Copernicus_DSM_COG_10_N37_00_W080_00_DEM"),
    (-34, 18, "Copernicus_DSM_COG_10_S34_00_E018_00_DEM"),
    (0, 0, "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"),
    (5, 7, "Copernicus_DSM_COG_10_N05_00_E007_00_DEM"),      # zero padding
    (-9, -123, "Copernicus_DSM_COG_10_S09_00_W123_00_DEM"),
])
def test_tile_id_known_names(lat0, lon0, expected):
    assert tile_id(lat0, lon0) == expected


def test_latitude_is_two_digits_and_longitude_three():
    """Copernicus pads them differently; a wrong width is a 404, not an error."""
    t = tile_id(7, 7)
    assert "_N07_00_E007_00_" in t


def test_the_ninety_metre_source_uses_its_own_prefix():
    assert tile_id(37, -80, 90).startswith(SOURCES[90][1])
    assert tile_id(37, -80, 30).startswith(SOURCES[30][1])
    assert tile_id(37, -80, 90) != tile_id(37, -80, 30)


def test_tile_url_points_at_the_matching_bucket():
    url = tile_url(37, -80, 30)
    assert url.startswith(f"https://{SOURCES[30][0]}.s3.amazonaws.com/")
    assert url.endswith(".tif")
    assert url.count(tile_id(37, -80, 30)) == 2      # directory and file


def test_an_unknown_resolution_is_refused():
    with pytest.raises(KeyError):
        tile_id(37, -80, 45)


# --------------------------------------------------------------------------- #
# the header beside a binary                                                   #
# --------------------------------------------------------------------------- #

def test_hdr_path_appends_rather_than_replaces():
    """A PACE file id carries a dot, so with_suffix would write PACE_OCI.hdr."""
    p = hdr_path("/tmp/PACE_OCI.20260422T195047_rdn")
    assert p.name == "PACE_OCI.20260422T195047_rdn.hdr"
    assert Path("/tmp/PACE_OCI.20260422T195047_rdn").with_suffix(".hdr").name == "PACE_OCI.hdr"


def test_hdr_path_on_an_ordinary_name():
    assert hdr_path("/tmp/emit20230422t195924_rdn").name == "emit20230422t195924_rdn.hdr"


def test_write_envi_header_states_what_isofit_reads_back(tmp_path):
    binary = tmp_path / "x_rdn"
    write_envi_header(hdr_path(binary), lines=7, samples=5, bands=3, dtype="float32",
                      wavelength=[400.0, 500.0, 600.0], fwhm=[10.0, 10.0, 10.0])
    text = hdr_path(binary).read_text()
    assert text.splitlines()[0].strip() == "ENVI"
    for field, value in (("lines", "7"), ("samples", "5"), ("bands", "3")):
        assert f"{field} = {value}" in text
    assert "interleave" in text
    assert "400" in text and "wavelength" in text


# --------------------------------------------------------------------------- #
# the sensor table                                                             #
# --------------------------------------------------------------------------- #

def test_every_alias_resolves_to_a_real_sensor():
    for alias, target in _ALIASES.items():
        assert target in SENSORS, f"alias {alias} points at {target}, which is not in SENSORS"


def test_every_sensor_can_name_its_radiance_file():
    """ISOFIT slices the file name back to recover the fid, so the pattern must carry it."""
    for name, spec in SENSORS.items():
        assert spec.code, f"{name} has no apply_oe sensor code"
        assert spec.fid, f"{name} has no fid pattern"
        assert "{fid}" in spec.rdn, f"{name}'s rdn pattern drops the fid: {spec.rdn!r}"


def test_unit_factor_is_a_positive_number_or_declared_unsupported():
    for name, spec in SENSORS.items():
        assert spec.unit_factor is None or spec.unit_factor > 0, name
        if spec.unit_factor is None:
            assert spec.converter, f"{name} has no unit_factor and no converter either"


def test_the_table_covers_every_instrument_the_package_reads():
    """A new reader without an ISOFIT route would otherwise fail only at run time."""
    expected = {"EMIT", "AVIRIS-3", "AVIRIS-5", "AVIRIS-NG", "AVIRIS-CLASSIC",
                "NEON", "ENMAP", "PRISMA", "TANAGER", "PACE", "DESIS"}
    assert set(SENSORS) == expected


def test_tested_flags_are_boolean_and_the_untested_ones_are_known():
    untested = {n for n, s in SENSORS.items() if not s.tested}
    for name, spec in SENSORS.items():
        assert isinstance(spec.tested, bool), name
    assert untested <= {"NEON"}, f"unexpected untested route(s): {untested - {'NEON'}}"


# --------------------------------------------------------------------------- #
# reading a dataset's identity                                                 #
# --------------------------------------------------------------------------- #

def _ds(sensor="EMIT", when="2023-04-22T19:59:24+0000", granule=""):
    return xr.Dataset(attrs={"sensor": sensor, "datetime": when, "granule": granule})


@pytest.mark.parametrize("given,expected", [
    ("EMIT", "EMIT"), ("emit", "EMIT"),
    ("AVIRIS3", "AVIRIS-3"), ("AVIRIS_3", "AVIRIS-3"), ("aviris3", "AVIRIS-3"),
    ("AVIRIS5", "AVIRIS-5"), ("AVIRISNG", "AVIRIS-NG"),
])
def test_sensor_spec_accepts_the_spellings_readers_produce(given, expected):
    key, spec = sensor_spec(_ds(given))
    assert key == expected
    assert spec is SENSORS[expected]


def test_an_unknown_sensor_says_what_it_knows():
    with pytest.raises(ValueError, match="no ISOFIT route"):
        sensor_spec(_ds("HYPERION"))


@pytest.mark.parametrize("raw", [
    "2023-04-22T19:59:24+0000", "2023-04-22T19:59:24Z",
    "2023-04-22T19:59:24+00:00", "2023-04-22T19:59:24",
])
def test_acquisition_time_normalises_to_naive_utc(raw):
    dt = acquisition_time(_ds(when=raw))
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) == (2023, 4, 22, 19, 59, 24)
    assert dt.tzinfo is None


def test_acquisition_time_converts_an_offset_rather_than_dropping_it():
    dt = acquisition_time(_ds(when="2023-04-22T21:59:24+02:00"))
    assert dt.hour == 19 and dt.tzinfo is None


def test_a_dataset_without_a_time_is_refused():
    with pytest.raises(ValueError, match="acquisition time"):
        acquisition_time(_ds(when=""))


def test_names_for_builds_the_id_isofit_will_parse_back():
    code, fid, rdn = names_for(_ds("EMIT"))
    assert code == "emit"
    assert fid == "emit20230422t195924"
    assert rdn == "emit20230422t195924_rdn"


def test_the_generic_route_stamps_the_date_into_the_code():
    """``code == "NA"`` means the generic route, which apply_oe keys by date."""
    generic = [n for n, s in SENSORS.items() if s.code == "NA"]
    if not generic:
        pytest.skip("no sensor uses the generic route")
    code, _, _ = names_for(_ds(generic[0]))
    assert code == "NA-20230422"


# --------------------------------------------------------------------------- #
# aerosol tables                                                               #
# --------------------------------------------------------------------------- #

def test_each_engine_offers_only_aerosols_it_implements():
    assert set(aerosols.AEROSOLS) <= set(ENGINES)
    assert set(aerosols.AEROSOLS["6s"]) == set(aerosols.SIXS_AEROSOL)
    for name in aerosols.AEROSOLS["LibRadTran"]:
        assert name in aerosols.LRT_AEROSOL


def test_sixs_aerosol_codes_are_the_integers_sixs_expects():
    for name, code in aerosols.SIXS_AEROSOL.items():
        assert isinstance(code, int) and 0 <= code <= 6, (name, code)


# --------------------------------------------------------------------------- #
# rewriting an apply_oe config                                                 #
# --------------------------------------------------------------------------- #

def _cfg():
    return {"forward_model": {"radiative_transfer": {"statevector": {"AOT550": {"init": 0.1}}}},
            "implementation": {"n_cores": 4}}


def test_apply_overrides_sets_by_slash_path():
    cfg = _cfg()
    changed, missing = apply_overrides(cfg, {"implementation/n_cores": 32})
    assert cfg["implementation"]["n_cores"] == 32
    assert missing == []
    assert changed == [("implementation/n_cores", 4, 32)]


def test_a_dotted_path_means_the_same_thing():
    cfg = _cfg()
    apply_overrides(cfg, {"implementation.n_cores": 16})
    assert cfg["implementation"]["n_cores"] == 16


def test_a_deep_path_reaches_the_leaf():
    cfg = _cfg()
    apply_overrides(cfg, {"forward_model/radiative_transfer/statevector/AOT550/init": 0.5})
    assert cfg["forward_model"]["radiative_transfer"]["statevector"]["AOT550"]["init"] == 0.5


def test_a_path_this_config_lacks_is_reported_not_raised():
    """apply_oe writes two configs and the water-vapour presolve has no aerosol term."""
    cfg = _cfg()
    changed, missing = apply_overrides(cfg, {"forward_model/radiative_transfer/statevector/AOT550/init": 0.5,
                                             "nothing/here": 1})
    assert missing == ["nothing/here"]
    assert len(changed) == 1


def test_overrides_never_create_new_keys():
    cfg = _cfg()
    apply_overrides(cfg, {"implementation/made_up": 1})
    assert "made_up" not in cfg["implementation"]


# --------------------------------------------------------------------------- #
# how many superpixel neighbours the analytical line is given                  #
# --------------------------------------------------------------------------- #

def _scene(tmp_path, lines, samples, valid=1.0):
    """The parts of an Inputs that neighbour counting reads."""
    import types
    out = tmp_path / "output"
    return types.SimpleNamespace(shape=(lines, samples, 285), stats={"valid_fraction": valid},
                                 output=lambda product: out / f"scene_{product}")


def _segment(scene, n):
    """Leave the label image a run with ``n`` superpixels would have written."""
    lbl = scene.output("lbl")
    lbl.parent.mkdir(parents=True, exist_ok=True)
    ny, nx, _ = scene.shape
    (np.arange(ny * nx) % n + 1).astype("<f4").tofile(lbl)
    hdr_path(lbl).write_text(f"ENVI\nsamples = {nx}\nlines = {ny}\nbands = 1\n"
                             "header offset = 0\ndata type = 4\ninterleave = bsq\nbyte order = 0\n")


def test_a_second_call_asks_for_the_neighbours_the_first_did(tmp_path):
    """A finished run is checked against the settings a new call would use, so
    those must not depend on whether the run has happened: a 60 x 60 window got
    45 the first time and 72 once its own label image existed, and every reuse
    then warned of "different settings"."""
    scene = _scene(tmp_path, 60, 60)
    first = resolve_neighbors(scene, 40)
    _segment(scene, 90)
    assert resolve_neighbors(scene, 40) == first == [45, 10]


def test_a_scene_with_fewer_segments_than_asked_for_still_lowers_the_cap(tmp_path):
    """The label image is what rescues a run that crashed asking for more
    neighbours than the scene had superpixels."""
    scene = _scene(tmp_path, 60, 60)
    _segment(scene, 30)
    assert neighbor_cap(scene, 40) == 24              # 0.8 x 30, below the estimate of 45


def test_a_window_large_enough_never_meets_the_cap(tmp_path):
    scene = _scene(tmp_path, 200, 200)
    first = resolve_neighbors(scene, 40)
    _segment(scene, 900)
    assert resolve_neighbors(scene, 40) == first == [100, 10]
