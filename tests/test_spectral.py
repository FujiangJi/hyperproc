"""hyperproc.spectral: wavelength addressing, continuum removal, derivatives.

Every test here has an answer known in advance: a straight line has a flat
continuum, a quadratic has a constant second derivative, and a Gaussian dip of
known depth at a known wavelength must come back with that depth at that
wavelength. The convex hull is checked against an independent implementation
rather than against itself.
"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from hyperproc import spectral as S
from hyperproc.spectral.continuum import _upper_hull


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


def _upper_hull_reference(wl, y):
    """Monotone chain, written independently of the implementation under test."""
    pts = list(zip(np.asarray(wl, float), np.asarray(y, float)))
    hull = []
    for p in pts:
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            cross = (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1)
            if cross >= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    hx = [p[0] for p in hull]; hy = [p[1] for p in hull]
    return np.interp(wl, hx, hy)


def test_band_at_picks_the_nearest_band():
    wl = np.array([400.0, 500.0, 600.0, 700.0])
    ds = _cube([0.1, 0.2, 0.3, 0.4], wl)
    b = S.band_at(ds, 590)
    assert float(b.values[0, 0]) == pytest.approx(0.3)
    assert b.attrs["wavelength_used"].startswith("600")
    assert b.attrs["band_index"] == 2

def test_band_at_refuses_when_nothing_is_near_enough():
    ds = _cube([0.1, 0.2], [400.0, 500.0])
    with pytest.raises(ValueError, match="no usable band within"):
        S.band_at(ds, 1600, tolerance=20)

def test_band_at_error_names_the_sensor_coverage():
    ds = _cube([0.1, 0.2], [400.0, 500.0])
    with pytest.raises(ValueError, match=r"400-500 nm"):
        S.band_at(ds, 2200)

def test_band_at_skips_bands_flagged_unusable():
    wl = np.array([400.0, 500.0, 600.0])
    ds = _cube([0.1, 0.2, 0.3], wl, good=[True, False, True])
    b = S.band_at(ds, 480, tolerance=200)
    assert b.attrs["wavelength_used"].startswith("400")     # 500 is nearer but flagged out

def test_hull_matches_an_independent_implementation():
    rng = np.random.default_rng(3)
    wl = np.linspace(400, 2400, 64)
    for _ in range(20):
        y = rng.uniform(0.05, 0.6, wl.size)
        got = _upper_hull(y[None, :], wl)[0]
        assert np.allclose(got, _upper_hull_reference(wl, y), atol=1e-9)

def test_a_straight_spectrum_has_a_flat_continuum():
    wl = np.linspace(400, 2400, 40)
    ds = _cube(0.1 + 0.0001 * (wl - 400), wl)
    cr = S.continuum_removal(ds)["reflectance"].values
    assert np.allclose(cr, 1.0, atol=1e-5)

def test_a_gaussian_dip_comes_back_at_its_own_depth_and_place():
    wl = np.linspace(2000, 2300, 61)
    depth, centre = 0.3, 2200.0
    spec = 0.4 * (1 - depth * np.exp(-0.5 * ((wl - centre) / 25.0) ** 2))
    ds = _cube(spec, wl)
    cr = S.continuum_removal(ds)["reflectance"].values[0, 0]
    assert 1.0 - cr.min() == pytest.approx(depth, abs=0.01)
    assert wl[np.argmin(cr)] == pytest.approx(centre, abs=6)

def test_continuum_never_spans_a_gap_in_usable_bands():
    wl = np.linspace(400, 2400, 40)
    good = np.ones(40, bool); good[18:24] = False
    ds = _cube(0.2 + 0.0 * wl, wl, good=good)
    cr = S.continuum_removal(ds)["reflectance"].values[0, 0]
    assert np.isnan(cr[18:24]).all()
    assert np.isfinite(cr[:18]).all() and np.isfinite(cr[24:]).all()

def test_continuum_keeps_the_nan_pattern():
    wl = np.linspace(400, 2400, 40)
    ds = _cube(np.linspace(0.1, 0.5, 40), wl)
    vals = ds["reflectance"].values.copy()
    vals[0, 0, 5] = np.nan
    ds["reflectance"] = (("y", "x", "wavelength"), vals)
    cr = S.continuum_removal(ds)["reflectance"].values
    assert np.isnan(cr[0, 0, 5])
    assert np.isfinite(cr[0, 1, 5])

def test_continuum_window_restricts_the_fit():
    wl = np.linspace(400, 2400, 40)
    ds = _cube(np.linspace(0.1, 0.5, 40), wl)
    cr = S.continuum_removal(ds, window=(2000, 2400))["reflectance"].values[0, 0]
    assert np.isnan(cr[wl < 2000]).all()
    assert np.isfinite(cr[wl >= 2000]).all()

def test_first_derivative_of_a_line_is_its_slope():
    wl = np.linspace(400, 1000, 61)                        # 10 nm spacing
    slope = 0.0003
    ds = _cube(0.1 + slope * (wl - 400), wl)
    d = S.derivative(ds, order=1, window=7, poly=2)["reflectance"].values
    assert np.allclose(d, slope, atol=1e-9)

def test_second_derivative_of_a_quadratic_is_constant():
    wl = np.linspace(400, 1000, 61)
    a = 2e-7
    ds = _cube(0.1 + a * (wl - 700) ** 2, wl)
    d = S.derivative(ds, order=2, window=9, poly=2)["reflectance"].values
    assert np.allclose(d, 2 * a, rtol=1e-4)

def test_derivative_stays_inside_usable_runs():
    wl = np.linspace(400, 1000, 61)
    good = np.ones(61, bool); good[20:30] = False
    ds = _cube(0.1 + 0.0003 * (wl - 400), wl, good=good)
    d = S.derivative(ds, order=1, window=7)["reflectance"].values[0, 0]
    assert np.isnan(d[20:30]).all()
    assert np.allclose(d[:20], 0.0003, atol=1e-9)

def test_derivative_argument_checks():
    ds = _cube(np.linspace(0.1, 0.5, 40), np.linspace(400, 2400, 40))
    with pytest.raises(ValueError, match="odd"):
        S.derivative(ds, window=6)
    with pytest.raises(ValueError, match="exceed poly"):
        S.derivative(ds, window=3, poly=3)
    with pytest.raises(ValueError, match="no derivative of order"):
        S.derivative(ds, order=3, window=7, poly=2)

def test_uneven_band_spacing_warns():
    wl = np.concatenate([np.arange(400, 700, 2.0), np.arange(700, 1000, 20.0)])
    ds = _cube(np.linspace(0.1, 0.4, wl.size), wl)
    with pytest.warns(UserWarning, match="band spacing varies"):
        S.derivative(ds, order=1, window=7)
