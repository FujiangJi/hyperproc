"""Published response functions: the registry, the parsers, and what they produce.

The network is touched only if an instrument is already cached, so this file
runs offline. What it always checks is the part that goes wrong silently: that
an alias resolves to the instrument you meant, that micrometres are recognised
as micrometres, and that a band's centre and width are recovered from its
response rather than assumed.
"""
from __future__ import annotations

import numpy as np
import pytest

from hyperproc.spectral import srf


# --------------------------------------------------------------------------- #
# the registry                                                                 #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name,expected", [
    ("SENTINEL2", "SENTINEL2A"), ("sentinel-2a", "SENTINEL2A"), ("S2B", "SENTINEL2B"),
    ("msi", "SENTINEL2A"), ("OLI", "LANDSAT8"), ("oli-2", "LANDSAT9"),
    ("ETM+", "LANDSAT7"), ("tm", "LANDSAT5"), ("Landsat 8", "LANDSAT8"),
    ("SuperDove", "PLANETSCOPE8"), ("PlanetScope", "PLANETSCOPE4"), ("psb.sd", "PLANETSCOPE8"),
])
def test_aliases_resolve(name, expected):
    assert srf.resolve(name) == expected


def test_unknown_sensor_lists_what_is_known():
    with pytest.raises(ValueError, match="unknown sensor"):
        srf.resolve("HYPERION")


def test_every_alias_points_somewhere_real():
    for alias, key in srf.ALIASES.items():
        assert key in srf.SOURCES or key in srf.NOMINAL, f"{alias} -> {key}"


def test_available_lists_every_instrument():
    text = srf.available()
    for key in list(srf.SOURCES) + list(srf.NOMINAL):
        assert key in text
    assert "measured" in text and "nominal" in text


# --------------------------------------------------------------------------- #
# nominal instruments need no network                                          #
# --------------------------------------------------------------------------- #

def test_planetscope_four_band():
    g = srf.fetch("PLANETSCOPE4", verbose=False)
    assert g["kind"] == "nominal" and g["response"] is None
    assert g["bands"] == ["Blue", "Green", "Red", "NIR"]
    assert np.allclose(g["wavelength"], [485, 545, 630, 820])
    assert np.allclose(g["fwhm"], [60, 90, 80, 80])


def test_superdove_eight_band_is_ordered_by_wavelength():
    g = srf.fetch("PLANETSCOPE8", verbose=False)
    assert len(g["bands"]) == 8
    assert np.all(np.diff(g["wavelength"]) > 0)
    assert g["bands"][0] == "CoastalBlue" and g["bands"][-1] == "NIR"


def test_nominal_target_asks_for_a_gaussian():
    t = srf.target("PLANETSCOPE8")
    assert t["method"] == "gaussian" and "nominal" in t["label"]
    assert "response" not in t


# --------------------------------------------------------------------------- #
# the parser helpers                                                           #
# --------------------------------------------------------------------------- #

def test_micrometres_are_recognised():
    assert np.allclose(srf._to_nm(np.array([0.48, 0.56, 2.2])), [480, 560, 2200])
    assert np.allclose(srf._to_nm(np.array([480.0, 560.0, 2200.0])), [480, 560, 2200])


def test_centre_and_width_come_from_the_response():
    fine = np.arange(300.0, 1000.0, 1.0)
    centre, fwhm = 665.0, 30.0
    sigma = fwhm / 2.3548200450309493
    R = np.exp(-0.5 * ((fine - centre) / sigma) ** 2)[None, :]
    c, f = srf._summarise(fine, R)
    assert c[0] == pytest.approx(centre, abs=0.5)
    assert f[0] == pytest.approx(fwhm, abs=1.5)


def test_an_empty_response_gives_nan_rather_than_a_wrong_number():
    fine = np.arange(300.0, 400.0, 1.0)
    c, f = srf._summarise(fine, np.zeros((1, fine.size)))
    assert np.isnan(c[0]) and np.isnan(f[0])


# --------------------------------------------------------------------------- #
# cached instruments, when they are there                                      #
# --------------------------------------------------------------------------- #

def _cached(key):
    return (srf.cache_dir() / f"{key}.npz").is_file()


@pytest.mark.parametrize("key,nbands,lo,hi", [
    ("SENTINEL2A", 13, 440, 2210), ("LANDSAT8", 9, 440, 2210), ("LANDSAT9", 9, 440, 2210),
    ("LANDSAT7", 7, 470, 2215), ("LANDSAT5", 6, 480, 2225),
])
def test_a_cached_instrument_parses_to_published_values(key, nbands, lo, hi):
    if not _cached(key):
        pytest.skip(f"{key} not cached; run srf.fetch({key!r}) once with network access")
    g = srf.fetch(key, verbose=False)
    assert g["kind"] == "measured"
    assert len(g["wavelength"]) == nbands
    assert lo <= g["wavelength"].min() and g["wavelength"].max() <= hi
    assert g["response"].shape == (nbands, g["response_wl"].size)
    assert (g["response"] >= 0).all()
    assert np.all(g["fwhm"] > 0)


def test_a_cached_measured_target_asks_for_its_response():
    if not _cached("SENTINEL2A"):
        pytest.skip("SENTINEL2A not cached")
    t = srf.target("SENTINEL2A")
    assert t["method"] == "response" and "measured" in t["label"]
    assert t["response"].shape[0] == t["wavelength"].size


def test_landsat_8_and_9_agree_on_their_shared_bands():
    """Independently published files; their common bands must line up."""
    if not (_cached("LANDSAT8") and _cached("LANDSAT9")):
        pytest.skip("Landsat 8/9 not cached")
    a, b = srf.fetch("LANDSAT8", verbose=False), srf.fetch("LANDSAT9", verbose=False)
    common = set(a["bands"]) & set(b["bands"])
    assert len(common) >= 8
    for name in common:
        wa = a["wavelength"][a["bands"].index(name)]
        wb = b["wavelength"][b["bands"].index(name)]
        assert abs(wa - wb) < 5.0, f"{name}: {wa:.1f} vs {wb:.1f} nm"
