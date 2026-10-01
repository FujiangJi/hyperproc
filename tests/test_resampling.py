"""Spectral resampling: weights, coverage, the guards, and the shapes accepted.

The answers are known in advance. Resampling onto the grid you are already on
must be the identity. A flat spectrum must stay flat, because the weights sum
to one. A linear ramp interpolated linearly must land exactly on the line. The
"box" method is checked against an independent transcription of the algorithm
it is meant to reproduce, not against itself.
"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from hyperproc.spectral import resampling as R


def _ds(wl, fwhm=None, ny=2, nx=3, values=None, good=None):
    wl = np.asarray(wl, dtype="float64")
    spec = np.asarray(values if values is not None else np.linspace(0.1, 0.5, wl.size), "float32")
    cube = np.broadcast_to(spec, (ny, nx, wl.size)).copy()
    coords = {"wavelength": wl, "y": np.arange(ny), "x": np.arange(nx)}
    if fwhm is not None:
        coords["fwhm"] = ("wavelength", np.broadcast_to(np.atleast_1d(fwhm), wl.shape).astype(float))
    if good is not None:
        coords["good_wavelength"] = ("wavelength", np.asarray(good, bool))
    return xr.Dataset({"reflectance": (("y", "x", "wavelength"), cube)}, coords=coords,
                      attrs={"sensor": "TEST", "stem": "scene"})


def _box_reference(c1, f1, c2, f2):
    """Spectral Python's BandResampler weights, transcribed independently."""
    from math import erf, sqrt
    ncdf = lambda x: 0.5 * (1.0 + erf(x / sqrt(2.0)))          # noqa: E731
    b1 = [(c - f / 2, c + f / 2) for c, f in zip(c1, f1)]
    b2 = [(c - f / 2, c + f / 2) for c, f in zip(c2, f2)]
    M = np.zeros((len(c2), len(c1)))
    for i, (lo2, hi2) in enumerate(b2):
        stdev = f2[i] / 2.3548200450309493
        contrib, idx = [], []
        for j, (lo1, hi1) in enumerate(b1):
            lo, hi = max(lo1, lo2), min(hi1, hi2)
            if hi <= lo:
                continue
            idx.append(j)
            contrib.append(ncdf((hi - c2[i]) / stdev) - ncdf((lo - c2[i]) / stdev))
        if contrib:
            contrib = np.array(contrib) / sum(contrib)
            M[i, idx] = contrib
    return M


# --------------------------------------------------------------------------- #
# the weights                                                                  #
# --------------------------------------------------------------------------- #

def test_build_fwhm_is_the_spacing():
    assert np.allclose(R.build_fwhm([400, 410, 420, 430]), 10.0)
    with pytest.raises(ValueError, match="at least two"):
        R.build_fwhm([500.0])


@pytest.mark.parametrize("method", ["gaussian", "box", "linear", "cubic"])
def test_rows_sum_to_one(method):
    s_wl = np.linspace(400, 2400, 201)
    t_wl = np.linspace(500, 2300, 61)
    M, _ = R.resampling_matrix(s_wl, t_wl, np.full(201, 10.0), np.full(61, 30.0), method=method)
    assert np.allclose(np.nansum(M, axis=1), 1.0)


@pytest.mark.parametrize("method", ["gaussian", "box", "linear", "cubic", "nearest"])
def test_a_flat_spectrum_stays_flat(method):
    s_wl = np.linspace(400, 2400, 201)
    flat = np.full(201, 0.27)
    out = R.resample(flat, source_wl=s_wl, source_fwhm=np.full(201, 10.0),
                     wavelengths=np.linspace(600, 2200, 33), fwhm=30.0, method=method)
    assert np.allclose(out, 0.27, atol=1e-6)


def test_resampling_onto_its_own_grid_is_the_identity():
    s_wl = np.linspace(400, 2400, 201)
    s_fw = np.full(201, 12.0)
    spec = 0.2 + 0.1 * np.sin(s_wl / 100.0)
    out = R.resample(spec, source_wl=s_wl, source_fwhm=s_fw,
                     wavelengths=s_wl, fwhm=s_fw, method="gaussian")
    assert np.allclose(out, spec, atol=2e-3)


def test_box_method_reproduces_the_reference_implementation():
    c1 = list(np.linspace(400, 2400, 121)); f1 = [16.0] * 121
    c2 = [490.0, 665.0, 865.0, 1610.0, 2190.0]; f2 = [65.0, 30.0, 20.0, 90.0, 180.0]
    M, _ = R.resampling_matrix(c1, c2, f1, f2, method="box", min_coverage=0.0)
    assert np.allclose(np.nan_to_num(M), _box_reference(c1, f1, c2, f2), atol=1e-12)


def test_linear_interpolation_lands_on_the_line():
    s_wl = np.linspace(400, 1000, 61)
    spec = 0.1 + 0.0004 * (s_wl - 400)
    t_wl = np.array([455.0, 632.5, 787.5])
    out = R.resample(spec, source_wl=s_wl, source_fwhm=np.full(61, 10.0),
                     wavelengths=t_wl, fwhm=10.0, method="linear")
    assert np.allclose(out, 0.1 + 0.0004 * (t_wl - 400), atol=1e-9)


def test_gaussian_uses_the_source_width_but_box_does_not():
    """The two differ, which is the point of offering both."""
    s_wl = np.linspace(400, 1000, 61)
    kw = dict(source_fwhm=np.full(61, 25.0), wavelengths=[700.0], fwhm=30.0)
    spec = np.exp(-0.5 * ((s_wl - 700) / 20.0) ** 2)
    g = R.resample(spec, source_wl=s_wl, method="gaussian", **kw)
    b = R.resample(spec, source_wl=s_wl, method="box", **kw)
    assert not np.isclose(g[0], b[0], atol=1e-3)


# --------------------------------------------------------------------------- #
# coverage                                                                     #
# --------------------------------------------------------------------------- #

def test_coverage_is_one_inside_and_zero_outside():
    s_wl = np.linspace(400, 2400, 201); s_fw = np.full(201, 10.0)
    cov = R.coverage_of([1000.0, 2600.0], [20.0, 20.0], s_wl, s_fw)
    assert cov[0] == pytest.approx(1.0, abs=1e-6)
    assert cov[1] == pytest.approx(0.0, abs=1e-6)


def test_coverage_is_a_half_at_the_edge():
    s_wl = np.linspace(400, 2400, 201); s_fw = np.full(201, 10.0)
    cov = R.coverage_of([2405.0], [40.0], s_wl, s_fw)     # centred on the last band's edge
    assert cov[0] == pytest.approx(0.5, abs=0.02)


def test_a_partly_covered_band_becomes_nan_rather_than_renormalising():
    """The defect this guard exists for: 43 % of a band should not look confident."""
    s_wl = np.linspace(400, 2400, 201); s_fw = np.full(201, 10.0)
    flat = np.full(201, 0.3)
    out, cov = R.resample(flat, source_wl=s_wl, source_fwhm=s_fw,
                          wavelengths=[2450.0], fwhm=200.0, min_coverage=0.5,
                          return_coverage=True)
    assert cov[0] < 0.5
    assert np.isnan(out[0])
    loose = R.resample(flat, source_wl=s_wl, source_fwhm=s_fw,
                       wavelengths=[2450.0], fwhm=200.0, min_coverage=0.0)
    assert np.isfinite(loose[0])                       # available if you ask for it knowingly


def test_bands_flagged_unusable_do_not_contribute_and_lower_coverage():
    s_wl = np.linspace(400, 2400, 201); s_fw = np.full(201, 10.0)
    usable = np.ones(201, bool)
    usable[(s_wl > 1340) & (s_wl < 1460)] = False        # a water-vapour gap
    full = R.coverage_of([1400.0], [40.0], s_wl, s_fw)
    gapped = R.coverage_of([1400.0], [40.0], s_wl, s_fw, usable=usable)
    assert full[0] > 0.99 and gapped[0] < 0.05
    M, _ = R.resampling_matrix(s_wl, [1000.0], s_fw, [40.0], usable=usable)
    assert np.all(np.nan_to_num(M)[0, ~usable] == 0.0)


# --------------------------------------------------------------------------- #
# the sharpening guard                                                         #
# --------------------------------------------------------------------------- #

def test_asking_for_finer_bands_than_the_source_is_refused():
    s_wl = np.linspace(400, 2400, 270); s_fw = np.full(270, 8.4)    # EMIT-like
    with pytest.raises(ValueError, match="narrower than the source"):
        R.resampling_matrix(s_wl, np.arange(500, 2000, 2.0), s_fw, 2.0)


def test_sharpening_can_be_allowed_explicitly():
    s_wl = np.linspace(400, 2400, 270); s_fw = np.full(270, 8.4)
    M, _ = R.resampling_matrix(s_wl, np.arange(500, 2000, 2.0), s_fw, 2.0, allow_sharpening=True)
    assert np.isfinite(M).any()


def test_coarsening_is_always_allowed():
    s_wl = np.linspace(400, 2400, 270); s_fw = np.full(270, 8.4)
    M, _ = R.resampling_matrix(s_wl, np.arange(500, 2000, 20.0), s_fw, 20.0)
    assert np.allclose(np.nansum(M, axis=1), 1.0)


# --------------------------------------------------------------------------- #
# naming a target                                                              #
# --------------------------------------------------------------------------- #

def test_step_and_fwhm_are_separate():
    t = R.target_grid(step=10.0, fwhm=15.0, wl_range=(400, 500))
    assert np.allclose(np.diff(t["wavelength"]), 10.0)
    assert np.allclose(t["fwhm"], 15.0)


def test_fwhm_defaults_to_the_step():
    t = R.target_grid(step=10.0, wl_range=(400, 500))
    assert np.allclose(t["fwhm"], 10.0)


def test_step_takes_its_range_from_the_source():
    t = R.target_grid(np.linspace(400, 2400, 201), step=100.0)
    assert t["wavelength"].min() >= 400 and t["wavelength"].max() <= 2400


def test_like_copies_another_band_set():
    other = _ds(np.linspace(450, 2350, 40), fwhm=25.0)
    t = R.target_grid(step=None, like=other)
    assert np.allclose(t["wavelength"], other.wavelength.values)
    assert np.allclose(t["fwhm"], 25.0)


def test_exactly_one_target_must_be_given():
    with pytest.raises(ValueError, match="exactly one"):
        R.target_grid(np.linspace(400, 2400, 10))
    with pytest.raises(ValueError, match="exactly one"):
        R.target_grid(np.linspace(400, 2400, 10), step=10.0, wavelengths=[500.0])


# --------------------------------------------------------------------------- #
# the shapes accepted                                                          #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("shape", [(201,), (7, 201), (4, 5, 201)])
def test_any_array_shape_with_wavelength_last(shape):
    s_wl = np.linspace(400, 2400, 201)
    values = np.broadcast_to(np.linspace(0.1, 0.5, 201), shape)
    out = R.resample(values, source_wl=s_wl, source_fwhm=np.full(201, 10.0),
                     step=50.0, fwhm=50.0)
    assert out.shape == shape[:-1] + (out.shape[-1],)
    assert np.isfinite(out).any()


def test_a_mismatched_last_axis_is_refused():
    with pytest.raises(ValueError, match="last axis"):
        R.resample(np.zeros((4, 17)), source_wl=np.linspace(400, 2400, 201), step=50.0)


def test_an_array_needs_its_source_wavelengths():
    with pytest.raises(ValueError, match="source_wl"):
        R.resample(np.zeros(201), step=50.0)


# --------------------------------------------------------------------------- #
# the dataset path                                                             #
# --------------------------------------------------------------------------- #

def test_dataset_gets_new_coordinates_and_provenance():
    ds = _ds(np.linspace(400, 2400, 201), fwhm=10.0)
    out = R.resample(ds, step=50.0, fwhm=50.0)
    assert out.sizes["wavelength"] == out.wavelength.size
    assert np.allclose(np.diff(out.wavelength.values), 50.0)
    assert np.allclose(out.fwhm.values, 50.0)
    assert "band_coverage" in out.coords
    assert "gaussian" in out.attrs["spectral_resampling"]
    assert out.sizes["y"] == ds.sizes["y"] and out.sizes["x"] == ds.sizes["x"]


def test_dataset_good_wavelength_follows_the_coverage():
    ds = _ds(np.linspace(400, 2400, 201), fwhm=10.0)
    out = R.resample(ds, wavelengths=[1000.0, 2600.0], fwhm=40.0, min_coverage=0.5)
    assert bool(out.good_wavelength.values[0]) and not bool(out.good_wavelength.values[1])
    assert np.isfinite(out.reflectance.values[..., 0]).all()
    assert np.isnan(out.reflectance.values[..., 1]).all()


def test_dataset_respects_flagged_bands():
    wl = np.linspace(400, 2400, 201)
    good = ~((wl > 1340) & (wl < 1460))
    ds = _ds(wl, fwhm=10.0, good=good)
    out = R.resample(ds, wavelengths=[1400.0], fwhm=40.0, min_coverage=0.5)
    assert not bool(out.good_wavelength.values[0])


def test_dataset_stays_lazy():
    ds = _ds(np.linspace(400, 2400, 201), fwhm=10.0, ny=8, nx=8).chunk({"y": 2, "x": 4})
    out = R.resample(ds, step=50.0, fwhm=50.0)
    assert out["reflectance"].chunks is not None
    assert np.isfinite(out["reflectance"].values).any()


def test_dataset_carries_other_layers_through():
    ds = _ds(np.linspace(400, 2400, 201), fwhm=10.0)
    ds["sza"] = (("y", "x"), np.full((2, 3), 30.0))
    out = R.resample(ds, step=100.0, fwhm=100.0)
    assert "sza" in out and float(out["sza"].values[0, 0]) == 30.0


# --------------------------------------------------------------------------- #
# a measured response, without needing one from the network                    #
# --------------------------------------------------------------------------- #

def _gauss_response(fine, centres, fwhms):
    sig = np.asarray(fwhms, dtype=float) / 2.3548200450309493
    return np.exp(-0.5 * ((fine[None, :] - np.asarray(centres)[:, None]) / sig[:, None]) ** 2)


def test_response_method_keeps_a_flat_spectrum_flat():
    s_wl = np.linspace(400, 2400, 201)
    fine = np.arange(380.0, 2420.0, 1.0)
    centres, fwhms = [490.0, 665.0, 865.0], [65.0, 30.0, 40.0]
    resp = _gauss_response(fine, centres, fwhms)
    M, _ = R.resampling_matrix(s_wl, centres, np.full(201, 10.0), fwhms,
                               method="response", response=resp, response_wl=fine)
    assert np.allclose(np.nansum(M, axis=1), 1.0)
    assert np.allclose(np.full(201, 0.31) @ np.nan_to_num(M).T, 0.31, atol=1e-6)


def test_response_method_needs_a_response():
    s_wl = np.linspace(400, 2400, 201)
    with pytest.raises(ValueError, match="needs response="):
        R.resampling_matrix(s_wl, [665.0], np.full(201, 10.0), [30.0], method="response")


def test_measured_and_gaussian_agree_to_about_a_percent():
    """A Gaussian of the same FWHM is a good approximation, not an identical one."""
    s_wl = np.linspace(400, 2400, 201); s_fw = np.full(201, 10.0)
    fine = np.arange(380.0, 2420.0, 1.0)
    centres, fwhms = [490.0, 665.0, 865.0, 1610.0], [65.0, 30.0, 40.0, 90.0]
    resp = _gauss_response(fine, centres, fwhms)
    spec = 0.2 + 0.15 * np.sin(s_wl / 250.0)
    m_resp, _ = R.resampling_matrix(s_wl, centres, s_fw, fwhms, method="response",
                                    response=resp, response_wl=fine)
    m_gauss, _ = R.resampling_matrix(s_wl, centres, s_fw, fwhms, method="gaussian")
    a, b = spec @ np.nan_to_num(m_resp).T, spec @ np.nan_to_num(m_gauss).T
    assert np.allclose(a, b, rtol=0.02)


# --------------------------------------------------------------------------- #
# a dead source band must stay local                                           #
# --------------------------------------------------------------------------- #

def _cube_with_one_dead_band():
    """A small cube where half the pixels carry NaN in one band at the far end."""
    s_wl = np.linspace(400.0, 2500.0, 211)
    s_fw = np.full(211, 12.0)
    spec = 0.2 + 0.15 * np.sin(s_wl / 250.0)
    cube = np.broadcast_to(spec, (4, 4, 211)).astype("float32").copy()
    cube[:2, :, -1] = np.nan            # one dead band, top half of the scene only
    ds = xr.Dataset(
        {"reflectance": (("y", "x", "wavelength"), cube)},
        coords={"wavelength": s_wl, "fwhm": ("wavelength", s_fw),
                "good_wavelength": ("wavelength", np.ones(211, bool))},
        attrs={"sensor": "TEST", "crs": "EPSG:4326"})
    return ds


def test_one_dead_band_does_not_empty_the_whole_spectrum():
    """``0.0 * nan`` is ``nan``, so a dense product spreads one dead band everywhere.

    On the PRISMA granule four unflagged bands near 2490 nm are NaN in some
    pixels, and that used to blank every resampled band of 31 % of the scene.
    """
    ds = _cube_with_one_dead_band()
    out = R.resample(ds, step=50.0, fwhm=60.0)["reflectance"].values
    finite = np.isfinite(out).sum(axis=-1)
    assert finite.min() > 0, "a pixel came back entirely NaN"
    # the affected pixels keep essentially every band the clean ones keep
    assert finite[:2].min() >= finite[2:].min() - 1


def test_a_dead_band_leaves_clean_pixels_bit_identical():
    ds = _cube_with_one_dead_band()
    out = R.resample(ds, step=50.0, fwhm=60.0)["reflectance"].values
    clean = R.resample(ds.isel(y=slice(2, 4)), step=50.0, fwhm=60.0)["reflectance"].values
    assert np.array_equal(np.nan_to_num(out[2:], nan=-1.0), np.nan_to_num(clean, nan=-1.0))


def test_a_target_band_losing_most_of_its_weight_is_nan_not_renormalised():
    """The per-pixel repair is held to the same coverage threshold as the grid test."""
    s_wl = np.linspace(400.0, 2500.0, 211)
    cube = np.full((1, 1, 211), 0.3, dtype="float32")
    dead = (s_wl > 1600.0) & (s_wl < 1900.0)          # a wide hole, not one band
    cube[..., dead] = np.nan
    ds = xr.Dataset(
        {"reflectance": (("y", "x", "wavelength"), cube)},
        coords={"wavelength": s_wl, "fwhm": ("wavelength", np.full(211, 12.0)),
                "good_wavelength": ("wavelength", np.ones(211, bool))},
        attrs={"sensor": "TEST", "crs": "EPSG:4326"})
    out = R.resample(ds, wavelengths=[1750.0, 600.0], fwhm=[200.0, 40.0])["reflectance"].values[0, 0]
    assert np.isnan(out[0]), "a band sitting inside the hole should be NaN"
    assert np.isfinite(out[1]), "a band far from the hole should be unaffected"
