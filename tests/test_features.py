"""hyperproc.features: spectral indices and absorption depths.

These reduce a spectrum to one number per pixel, so the answers are checked
against hand computation and against synthetic features of known depth and
position. The formula parser is checked by trying to make it do something
other than arithmetic.
"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from hyperproc import features as F
from hyperproc import spectral as S


def _cube(spectra, wl, good=None, ny=2, nx=3):
    """A (ny, nx, nwl) dataset whose every pixel carries the same spectrum."""
    spectra = np.asarray(spectra, dtype="float32")
    cube = np.broadcast_to(spectra, (ny, nx, spectra.size)).copy()
    coords = {"wavelength": np.asarray(wl, dtype="float64"),
              "y": np.arange(ny), "x": np.arange(nx)}
    if good is not None:
        coords["good_wavelength"] = ("wavelength", np.asarray(good, dtype=bool))
    return xr.Dataset({"reflectance": (("y", "x", "wavelength"), cube)}, coords=coords,
                      attrs={"sensor": "TEST", "stem": "scene"})


def _chunked(ds):
    return ds.chunk({"y": 1, "x": 2})


def test_ndvi_matches_the_hand_computation():
    wl = np.array([660.0, 860.0])
    ds = _cube([0.05, 0.45], wl)
    got = F.index(ds, "NDVI")
    assert float(got.values[0, 0]) == pytest.approx((0.45 - 0.05) / (0.45 + 0.05))
    assert got.name == "NDVI"
    assert got.attrs["reference"].startswith("Rouse")
    assert "R860=860" in got.attrs["bands_used"]

def test_a_custom_formula_works_and_is_recorded():
    ds = _cube([0.05, 0.45], [670.0, 800.0])
    got = F.index(ds, "(R800 - R670) / (R800 + R670)")
    assert float(got.values[0, 0]) == pytest.approx((0.45 - 0.05) / 0.5)
    assert got.attrs["formula"].startswith("(R800")

def test_a_formula_may_call_the_allowed_functions():
    ds = _cube([0.25], [1510.0])
    got = F.index(ds, "log(1/R1510)")
    assert float(got.values[0, 0]) == pytest.approx(np.log(1 / 0.25))

def test_formula_without_bands_is_refused():
    ds = _cube([0.2], [800.0])
    with pytest.raises(ValueError, match="names no bands"):
        F.index(ds, "1 + 2")

@pytest.mark.parametrize("expr", [
    "__import__('os').system('ls')",
    "R800.values",
    "[R800 for _ in range(3)]",
    "R800 if R800 else 0",
    "open('/etc/passwd')",
])
def test_formulas_cannot_do_anything_but_arithmetic(expr):
    ds = _cube([0.2], [800.0])
    with pytest.raises(ValueError):
        F.index(ds, expr)

def test_index_refuses_a_wavelength_the_sensor_lacks():
    ds = _cube([0.05, 0.45], [660.0, 860.0])              # no SWIR, as on DESIS
    with pytest.raises(ValueError, match="no usable band"):
        F.index(ds, "NDII")

def test_describe_indices_reports_availability():
    ds = _cube([0.05, 0.45], [660.0, 860.0])
    text = F.describe_indices(ds)
    assert "NDVI" in text and "available" in text
    assert "no bands" in text                              # the SWIR ones

def test_band_depth_recovers_a_known_feature():
    wl = np.linspace(1950, 2350, 81)
    depth, centre = 0.25, 2210.0
    spec = 0.35 * (1 - depth * np.exp(-0.5 * ((wl - centre) / 30.0) ** 2))
    ds = _cube(spec, wl)
    bd = F.band_depth(ds, "cellulose")
    assert float(bd["depth"].values[0, 0]) == pytest.approx(depth, abs=0.02)
    assert float(bd["position"].values[0, 0]) == pytest.approx(centre, abs=10)
    assert float(bd["area"].values[0, 0]) > 0
    assert bd.attrs["band_depth_feature"] == "cellulose"

def test_band_depth_of_a_featureless_spectrum_is_zero():
    wl = np.linspace(1950, 2350, 81)
    ds = _cube(np.full(wl.size, 0.3), wl)
    bd = F.band_depth(ds, (2000, 2300))
    assert float(bd["depth"].values[0, 0]) == pytest.approx(0.0, abs=1e-5)

def test_band_depth_rejects_an_unknown_feature():
    ds = _cube(np.linspace(0.1, 0.5, 40), np.linspace(400, 2400, 40))
    with pytest.raises(ValueError, match="unknown feature"):
        F.band_depth(ds, "chlorophyl")

def test_band_depth_needs_bands_in_the_window():
    ds = _cube([0.2, 0.3], [400.0, 500.0])
    with pytest.raises(ValueError):
        F.band_depth(ds, (2000, 2300))

def test_every_feature_works_on_a_chunked_cube():
    """Real granules arrive as dask arrays; a numpy-only test hides whole classes of bug."""
    wl = np.linspace(1950, 2350, 81)
    depth, centre = 0.25, 2210.0
    spec = 0.35 * (1 - depth * np.exp(-0.5 * ((wl - centre) / 30.0) ** 2))
    ds = _chunked(_cube(spec, wl, ny=4, nx=6))
    assert ds["reflectance"].chunks is not None

    cr = S.continuum_removal(ds)["reflectance"]
    assert cr.chunks is not None                           # still lazy
    assert 1.0 - float(cr.values.min()) == pytest.approx(depth, abs=0.02)

    d1 = S.derivative(ds, order=1, window=7)["reflectance"]
    assert d1.chunks is not None and np.isfinite(d1.values).any()

    bd = F.band_depth(ds, (2000, 2300))
    assert float(bd["depth"].values[0, 0]) == pytest.approx(depth, abs=0.02)
    assert float(bd["position"].values[0, 0]) == pytest.approx(centre, abs=10)
    assert np.isfinite(bd["area"].values).all()

def test_index_works_on_a_chunked_cube():
    ds = _chunked(_cube([0.05, 0.45], [660.0, 860.0], ny=4, nx=6))
    got = F.index(ds, "NDVI")
    assert float(got.values[0, 0]) == pytest.approx(0.8)

def test_band_depth_position_is_nan_where_the_spectrum_is_missing():
    wl = np.linspace(2000, 2300, 41)
    ds = _cube(np.full(wl.size, 0.3), wl, ny=2, nx=2)
    vals = ds["reflectance"].values.copy()
    vals[0, 0, :] = np.nan
    ds["reflectance"] = (("y", "x", "wavelength"), vals)
    bd = F.band_depth(_chunked(ds), (2000, 2300))
    assert np.isnan(bd["position"].values[0, 0])
    assert np.isfinite(bd["position"].values[1, 1])
