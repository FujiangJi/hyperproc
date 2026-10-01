"""Satellite BRDF normalisation: kernels, spectral mapping, sampling, c-factor.

The checks that matter are the ones with a known answer:

* the package kernels reproduce the RossThick-LiSparseReciprocal pair the
  MCD43A1 weights were fitted with, to floating-point precision;
* the c-factor is exactly 1 when the target geometry is the observed one;
* a synthetic scene whose reflectance follows the model exactly comes out flat
  in view angle after the correction, which is the whole point of the method.
"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from hyperproc.correct import cfactor, mcd43
from hyperproc.correct.kernels import geometric_kernel, volume_kernel

PI = np.pi


# --------------------------------------------------------------------------- #
# the kernels the MODIS product was fitted with                                #
# --------------------------------------------------------------------------- #

def _ross_thick_reference(sza, vza, raa):
    """RossThick as written in the kernel-driven BRDF literature, independently."""
    raa = np.abs(raa)
    raa = np.where(raa > PI, 2 * PI - raa, raa)
    cos_xi = np.clip(np.cos(sza) * np.cos(vza) + np.sin(sza) * np.sin(vza) * np.cos(raa), -1, 1)
    xi = np.arccos(cos_xi)
    return ((PI / 2 - xi) * cos_xi + np.sin(xi)) / (np.cos(sza) + np.cos(vza)) - PI / 4


def _li_sparse_r_reference(sza, vza, raa, h_b=2.0, b_r=1.0):
    """LiSparseReciprocal, independently, with the MODIS crown shape."""
    raa = np.abs(raa)
    raa = np.where(raa > PI, 2 * PI - raa, raa)
    s = np.arctan(b_r * np.tan(sza))
    v = np.arctan(b_r * np.tan(vza))
    sec = lambda a: 1.0 / np.cos(a)                                     # noqa: E731
    cos_zeta = np.cos(s) * np.cos(v) + np.sin(s) * np.sin(v) * np.cos(raa)
    d2 = np.tan(s) ** 2 + np.tan(v) ** 2 - 2 * np.tan(s) * np.tan(v) * np.cos(raa)
    cos_t = np.clip(h_b * np.sqrt(d2 + (np.tan(s) * np.tan(v) * np.sin(raa)) ** 2) / (sec(s) + sec(v)), -1, 1)
    t = np.arccos(cos_t)
    overlap = (t - np.sin(t) * cos_t) * (sec(s) + sec(v)) / PI
    return overlap - sec(s) - sec(v) + 0.5 * (1 + cos_zeta) * sec(v) * sec(s)


@pytest.fixture(scope="module")
def angles():
    sza = np.radians(np.array([10.0, 25.0, 45.0, 60.0, 70.0]))
    vza = np.radians(np.array([0.0, 5.0, 15.0, 30.0, 55.0]))
    raa = np.radians(np.array([0.0, 40.0, 90.0, 170.0, 200.0, 300.0, 359.0]))
    return np.meshgrid(sza, vza, raa, indexing="ij")


def test_ross_thick_matches_reference(angles):
    s, v, r = angles
    assert np.allclose(volume_kernel("ross_thick", s, v, r), _ross_thick_reference(s, v, r), atol=1e-9)


def test_li_sparse_r_matches_reference(angles):
    s, v, r = angles
    got = geometric_kernel("li_sparse_r", s, v, r, b_r=1.0, h_b=2.0)
    assert np.allclose(got, _li_sparse_r_reference(s, v, r), atol=1e-9)


def test_relative_azimuth_folding_is_a_no_op(angles):
    """The kernels use cos(raa) and sin(raa)^2 only, so 340 deg and 20 deg agree."""
    s, v, _ = angles
    a, b = np.radians(20.0), np.radians(340.0)
    for kernel, fn in (("ross_thick", volume_kernel), ("li_sparse_r", geometric_kernel)):
        assert np.allclose(fn(kernel, s, v, np.full_like(s, a)),
                           fn(kernel, s, v, np.full_like(s, b)), atol=1e-9)


# --------------------------------------------------------------------------- #
# the ratio                                                                    #
# --------------------------------------------------------------------------- #

def test_c_factor_is_one_at_the_observed_geometry():
    rng = np.random.default_rng(0)
    params = np.stack([rng.uniform(0.05, 0.5, (20, 7)),
                       rng.uniform(0.0, 0.3, (20, 7)),
                       rng.uniform(0.0, 0.1, (20, 7))], axis=-1).astype("float32")
    sza = rng.uniform(15, 65, 20).astype("float32")
    vza = rng.uniform(0, 50, 20).astype("float32")
    raa = rng.uniform(0, 360, 20).astype("float32")
    # target == observed for every pixel: the ratio is identically one
    c_id = np.stack([cfactor.c_factor(params[i], sza[i], vza[i], raa[i], sza_ref=float(sza[i]),
                                      vza_ref=float(vza[i]), raa_ref=float(raa[i])) for i in range(20)])
    ok = np.isfinite(c_id)
    assert ok.mean() > 0.9
    assert np.allclose(c_id[ok], 1.0, atol=1e-6)
    # the rest are random weight combinations whose modelled reflectance is negative,
    # where a ratio would be meaningless; the guard must reject exactly those
    modelled = np.stack([cfactor.model_reflectance(params[i], sza[i], vza[i], raa[i]) for i in range(20)])
    assert (modelled[~ok] <= cfactor.MIN_MODEL).all()


def test_c_factor_propagates_missing_parameters():
    params = np.full((3, 7, 3), np.nan, dtype="float32")
    params[0] = np.array([[0.2, 0.05, 0.01]] * 7)
    c = cfactor.c_factor(params, np.float32([30, 30, 30]), np.float32([20, 20, 20]), np.float32([60, 60, 60]))
    assert np.isfinite(c[0]).all()
    assert np.isnan(c[1:]).all()


def test_c_factor_clipping():
    params = np.zeros((1, 7, 3), dtype="float32")
    params[..., 0] = 1e-6                                  # a degenerate model
    params[..., 1] = 0.5
    c = cfactor.c_factor(params, np.float32([70]), np.float32([60]), np.float32([180]), clip=(0.5, 1.5))
    assert np.all(np.isnan(c) | ((c >= 0.5) & (c <= 1.5)))


# --------------------------------------------------------------------------- #
# spectral mapping                                                             #
# --------------------------------------------------------------------------- #

def test_band_weights_are_an_average():
    wl = np.linspace(380, 2500, 300)
    for mode in cfactor.SPECTRAL_MODES:
        w = cfactor.band_weights(wl, mode)
        assert w.shape == (7, wl.size)
        assert np.allclose(w.sum(axis=0), 1.0)
        assert (w >= 0).all()


def test_interp_weights_are_exact_at_the_modis_centres():
    centres = [mcd43.MODIS_CENTRES[b] for b in mcd43.MODIS_BANDS]
    w = cfactor.band_weights(centres, "interp")
    assert np.allclose(w, np.eye(7), atol=1e-6)


def test_nearest_weights_are_one_hot_and_match_band_map():
    wl = np.array([412.0, 660.0, 865.0, 1240.0, 1610.0, 2200.0])
    w = cfactor.band_weights(wl, "nearest")
    assert set(np.unique(w)) <= {0.0, 1.0}
    assert np.array_equal(np.argmax(w, axis=0), cfactor.band_map(wl))
    assert cfactor.band_map([660.0])[0] == 0            # MODIS band 1
    assert cfactor.band_map([865.0])[0] == 1            # MODIS band 2


def test_interp_is_smoother_than_nearest():
    wl = np.linspace(400, 2400, 400)
    p = np.zeros((1, 7, 3), dtype="float32")
    p[..., 0] = np.linspace(0.1, 0.4, 7)                 # a spectrally varying surface
    p[..., 1] = np.linspace(0.02, 0.2, 7)
    c = cfactor.c_factor(p, np.float32([35]), np.float32([25]), np.float32([120]))
    steps = {m: np.abs(np.diff(c @ cfactor.band_weights(wl, m))).max() for m in cfactor.SPECTRAL_MODES}
    assert steps["interp"] < steps["nearest"]


# --------------------------------------------------------------------------- #
# the parameter stack                                                          #
# --------------------------------------------------------------------------- #

def _synthetic_params(ny=8, nx=10, iso=0.25, vol=0.05, geo=0.01):
    vals = np.zeros((ny, nx, 7, 3), dtype="float32")
    vals[..., 0] = iso
    vals[..., 1] = vol
    vals[..., 2] = geo
    transform = (0.01, 0.0, -100.0, 0.0, -0.01, 40.0)
    return mcd43.Params(vals, transform, date="2023-04-22")


def test_sample_bilinear_recovers_a_ramp():
    p = _synthetic_params(ny=6, nx=6)
    ramp = np.arange(6, dtype="float32")[None, :] * np.ones((6, 1), dtype="float32")
    p.values[..., 0, 0] = ramp                                  # band 1 iso = column index
    lon = -100.0 + (np.array([1.5, 2.0, 3.5]) + 0.5) * 0.01     # cell centres of columns 1.5, 2, 3.5
    lat = np.full(3, 40.0 - 2.5 * 0.01)
    got = p.sample(lon, lat)[..., 0, 0]
    assert np.allclose(got, [1.5, 2.0, 3.5], atol=1e-4)


def test_sample_skips_gaps_and_returns_nan_when_surrounded():
    p = _synthetic_params(ny=5, nx=5)
    p.values[:, :, :, :] = np.nan
    p.values[2, 2] = 0.3
    lon = np.array([-100.0 + 2.5 * 0.01, -100.0 + 0.5 * 0.01])
    lat = np.array([40.0 - 2.5 * 0.01, 40.0 - 0.5 * 0.01])
    got = p.sample(lon, lat)[..., 0, 0]
    assert np.isclose(got[0], 0.3)
    assert np.isnan(got[1])


def test_sample_outside_the_grid_is_nan():
    p = _synthetic_params()
    got = p.sample(np.array([-150.0]), np.array([10.0]))
    assert np.isnan(got).all()


def test_geotiff_round_trip(tmp_path):
    p = _synthetic_params()
    p.values[3, 4] = np.nan
    p.quality = np.zeros(p.shape + (7,), dtype="uint8")
    p.snow = np.zeros(p.shape, dtype="uint8")
    p.snow[0, 0] = 1
    back = mcd43.read(p.to_geotiff(tmp_path / "params.tif"))
    assert np.allclose(back.values[0, 0], p.values[0, 0], atol=1e-6)
    assert np.isnan(back.values[3, 4]).all()
    assert back.date == "2023-04-22"
    assert back.snow[0, 0] == 1
    masked = back.masked(qa_max=0, snow=True)
    assert np.isnan(masked.values[0, 0]).all()


def test_masked_drops_low_quality():
    p = _synthetic_params()
    p.quality = np.zeros(p.shape + (7,), dtype="uint8")
    p.quality[1, 1, :] = 2
    out = p.masked(qa_max=1, snow=False)
    assert np.isnan(out.values[1, 1]).all()
    assert np.isfinite(out.values[0, 0]).all()


# --------------------------------------------------------------------------- #
# whole-scene normalisation                                                    #
# --------------------------------------------------------------------------- #

def _scene(ny=12, nx=40, iso=0.25, vol=0.06, geo=0.012):
    """A scene whose reflectance follows the MODIS model exactly.

    The instrument bands sit on the MODIS centres, so the spectral mapping is
    the identity and any residual angular trend is the correction's fault.
    """
    p = _synthetic_params(ny=ny + 4, nx=nx + 4, iso=iso, vol=vol, geo=geo)
    lon = -100.0 + (np.arange(nx) + 2.5) * 0.01
    lat = 40.0 - (np.arange(ny) + 2.5) * 0.01
    lon2d, lat2d = np.meshgrid(lon, lat)
    sza = np.full((ny, nx), 35.0, dtype="float32")
    vza = np.tile(np.linspace(-50, 50, nx).astype("float32"), (ny, 1))    # across-track sweep
    raa = np.where(vza < 0, 40.0, 220.0).astype("float32")                # sign flip = azimuth flip
    vza = np.abs(vza)
    wl = np.array([mcd43.MODIS_CENTRES[b] for b in mcd43.MODIS_BANDS], dtype="float64")
    params = np.broadcast_to(p.values[0, 0], (ny, nx, 7, 3))
    rho = cfactor.model_reflectance(params, sza, vza, raa)
    ds = xr.Dataset(
        {"reflectance": (("y", "x", "wavelength"), rho.astype("float32")),
         "lon": (("y", "x"), lon2d), "lat": (("y", "x"), lat2d),
         "sza": (("y", "x"), sza), "vza": (("y", "x"), vza), "raa": (("y", "x"), raa)},
        coords={"wavelength": wl, "y": np.arange(ny), "x": np.arange(nx)},
        attrs={"sensor": "TEST", "stem": "scene", "datetime": "2023-04-22T19:00:00+0000"})
    return ds, p


def test_nbar_flattens_a_model_scene():
    ds, p = _scene()
    out = cfactor.nbar(ds, params=p, sza_ref="observed", qa_max=None, mask_snow=False, verbose=False)
    r = out["reflectance"].values
    assert np.isfinite(r).all()
    # every pixel should land on the nadir model reflectance, the same everywhere
    spread = r.std(axis=(0, 1)) / r.mean(axis=(0, 1))
    assert (spread < 1e-5).all(), spread
    before = ds["reflectance"].values
    assert before.std(axis=(0, 1)).max() > 1e-3          # there was a trend to remove


def test_nbar_target_sza_changes_the_level_not_the_flatness():
    ds, p = _scene()
    out = cfactor.nbar(ds, params=p, sza_ref=45.0, qa_max=None, mask_snow=False, verbose=False)
    r = out["reflectance"].values
    assert (r.std(axis=(0, 1)) / r.mean(axis=(0, 1)) < 1e-5).all()
    nadir45 = cfactor.model_reflectance(p.values[0, 0], 45.0, 0.0, 0.0)
    assert np.allclose(r.mean(axis=(0, 1)), nadir45, rtol=1e-4)


def test_nbar_records_provenance_and_validity():
    ds, p = _scene()
    out = cfactor.nbar(ds, params=p, qa_max=None, mask_snow=False, verbose=False)
    assert out.attrs["stem"] == "scene_brdf"
    assert "c-factor" in out.attrs["brdf_method"]
    assert out.attrs["brdf_target"].startswith("sza=45")
    assert float(out.attrs["brdf_coverage"]) == 1.0
    assert out["brdf_valid"].dtype == np.uint8 and int(out["brdf_valid"].min()) == 1
    assert float(out.attrs["brdf_unobserved"]) == 0.0
    assert out["c_factor"].sizes["modis_band"] == 7


def test_coverage_ignores_pixels_the_sensor_never_saw():
    """Off-swath cells have no geometry; they must not count against MODIS."""
    ds, p = _scene()
    ds = ds.copy()
    for v in ("sza", "vza", "raa"):
        a = np.array(ds[v].values, copy=True)
        a[:, :10] = np.nan                                    # a void strip, as an ortho grid has
        ds[v] = (("y", "x"), a)
    out = cfactor.nbar(ds, params=p, qa_max=None, mask_snow=False, verbose=False)
    assert float(out.attrs["brdf_coverage"]) == 1.0           # every observed pixel was corrected
    assert float(out.attrs["brdf_unobserved"]) == pytest.approx(10 / 40)
    assert set(np.unique(out["brdf_valid"].values)) == {1, 2}


def test_nbar_leaves_pixels_without_parameters_alone():
    ds, p = _scene()
    p.values[:, :6] = np.nan                                  # blank the west edge of the MODIS grid
    out = cfactor.nbar(ds, params=p, fill="none", qa_max=None, mask_snow=False, verbose=False)
    valid = out["brdf_valid"].values.astype(bool)
    assert not valid.all() and valid.any()
    untouched = ~valid
    assert np.allclose(out["reflectance"].values[untouched], ds["reflectance"].values[untouched])
    assert float(out.attrs["brdf_coverage"]) < 1.0


def test_nbar_fill_modes_cover_every_pixel():
    ds, p = _scene()
    p.values[:, :6] = np.nan
    for how in ("median", "nearest"):
        out = cfactor.nbar(ds, params=p, fill=how, qa_max=None, mask_snow=False, verbose=False)
        assert np.isfinite(out["reflectance"].values).all()
        assert np.isfinite(out["c_factor"].values).all()


def test_nbar_needs_geometry():
    ds, p = _scene()
    with pytest.raises(ValueError, match="geometry"):
        cfactor.nbar(ds.drop_vars("sza"), params=p, verbose=False)


def test_view_profile_reports_the_flattening():
    ds, p = _scene()
    out = cfactor.nbar(ds, params=p, sza_ref="observed", qa_max=None, mask_snow=False, verbose=False)
    prof = cfactor.view_profile(ds, out, wavelength=858.5, step=5.0)
    assert prof["vza"].size > 3
    assert abs(prof["slope_after"]) < abs(prof["slope_before"]) / 10


# --------------------------------------------------------------------------- #
# scene metadata                                                               #
# --------------------------------------------------------------------------- #

def test_bounds_and_date_from_a_dataset():
    ds, _ = _scene()
    w, s, e, n = mcd43.bounds_of(ds)
    assert -100.0 < w < e < -99.5 and 39.5 < s < n < 40.0
    assert mcd43.date_of(ds) == "2023-04-22"


def test_date_falls_back_to_the_granule_name():
    ds = xr.Dataset(attrs={"granule": "EMIT_L2A_RFL_001_20230422T195924_2311213_002"})
    assert mcd43.date_of(ds) == "2023-04-22"


def test_grid_snaps_outward_and_is_shared_between_overlapping_scenes():
    t1, nx1, ny1 = mcd43.grid_for((-121.0, 34.0, -120.0, 35.0))
    t2, nx2, ny2 = mcd43.grid_for((-120.5, 34.2, -119.5, 35.2))
    step = mcd43.RES_DEG
    assert abs(((t1[2] - t2[2]) / step) - round((t1[2] - t2[2]) / step)) < 1e-6
    assert abs(((t1[5] - t2[5]) / step) - round((t1[5] - t2[5]) / step)) < 1e-6


# --------------------------------------------------------------------------- #
# adapting the MODIS grid to the image                                         #
# --------------------------------------------------------------------------- #

def test_resolution_of_a_projected_grid_converts_metres():
    ds = xr.Dataset(coords={"x": np.arange(10) * 30.0 + 5e5, "y": 4e6 - np.arange(10) * 30.0},
                    attrs={"crs": "EPSG:32610"})
    assert mcd43.resolution_of(ds) == pytest.approx(30.0 / 111320.0, rel=1e-6)


def test_resolution_of_a_geographic_grid_is_taken_as_is():
    step = 0.000542
    ds = xr.Dataset(coords={"x": np.arange(10) * step, "y": -np.arange(10) * step},
                    attrs={"crs": "EPSG:4326"})
    assert mcd43.resolution_of(ds) == pytest.approx(step, rel=1e-6)


def test_resolution_of_a_rotated_swath_counts_both_axes():
    """A swath is rotated, so the step along a row is not the change in longitude alone."""
    n, step = 20, 0.01
    j, i = np.meshgrid(np.arange(n), np.arange(n), indexing="xy")
    ang = np.radians(40.0)
    lat0 = 45.0
    lon = (j * np.cos(ang) - i * np.sin(ang)) * step / np.cos(np.radians(lat0))
    lat = lat0 - (j * np.sin(ang) + i * np.cos(ang)) * step
    ds = xr.Dataset({"lon": (("y", "x"), lon), "lat": (("y", "x"), lat)})
    assert mcd43.resolution_of(ds) == pytest.approx(step, rel=0.02)


def test_step_for_never_goes_finer_than_the_product():
    fine = xr.Dataset(coords={"x": np.arange(10) * 30.0, "y": -np.arange(10) * 30.0},
                      attrs={"crs": "EPSG:32610"})
    res, k = mcd43.step_for(fine)
    assert k == 1 and res == mcd43.RES_DEG


def test_step_for_aggregates_for_a_coarse_image():
    coarse = xr.Dataset(coords={"x": np.arange(10) * 1500.0, "y": -np.arange(10) * 1500.0},
                        attrs={"crs": "EPSG:32610"})
    res, k = mcd43.step_for(coarse)
    assert k == 3                                      # 1500 m / 464 m, rounded down
    assert res == pytest.approx(3 * mcd43.RES_DEG)
    assert res * 111320 <= 1500.0                      # never coarser than the pixel


def test_step_for_honours_an_explicit_resolution():
    assert mcd43.step_for(None, res=2 * mcd43.RES_DEG) == (pytest.approx(2 * mcd43.RES_DEG), 2)
    assert mcd43.step_for(None)[1] == 1


def test_grid_pads_by_at_least_two_cells():
    res = 5 * mcd43.RES_DEG
    transform, nx, ny = mcd43.grid_for((-121.0, 34.0, -120.9, 34.1), res=res, pad=0.0)
    assert transform[2] <= -121.0 - 2 * res
    assert transform[5] >= 34.1 + 2 * res


def test_nbar_defaults_to_nearest_band_mapping():
    ds, p = _scene()
    out = cfactor.nbar(ds, params=p, qa_max=None, mask_snow=False, verbose=False)
    assert out.attrs["brdf_spectral"] == "nearest"
    assert out.attrs["brdf_parameter_step_m"] == f"{0.01 * 111320:.0f}"


def test_date_of_reads_a_granule_path():
    """The preflight needs the date before the cube is open, so a path must work."""
    cases = {
        "EMIT_L2A_RFL_001_20230422T195924_2311213_002.nc": "2023-04-22",
        "/data/x/PRS_L1_STD_OFFL_20230422103045_20230422103049_0001.he5": "2023-04-22",
        "PACE_OCI.20260422T195047.L1B.V3.nc": "2026-04-22",
        "ENMAP01-____L1C-DT0000004950_20220806T103728Z_001_V010111-SPECTRAL_IMAGE.TIF": "2022-08-06",
    }
    for name, want in cases.items():
        assert mcd43.date_of(name) == want, name


def test_date_of_prefers_the_dataset_timestamp():
    ds = xr.Dataset(attrs={"datetime": "2021-07-04T12:00:00+0000",
                           "granule": "SENSOR_20230422T195924"})
    assert mcd43.date_of(ds) == "2021-07-04"


def test_date_of_rejects_a_name_without_a_date():
    with pytest.raises(ValueError, match="no acquisition date"):
        mcd43.date_of("some_file_without_a_date.tif")


def _angular_scene(ny=60, nx=60, iso=0.3, vol=0.12, geo=0.02):
    """A scene that spans a full range of relative azimuth, reflectance from the model."""
    p = _synthetic_params(ny=ny + 4, nx=nx + 4, iso=iso, vol=vol, geo=geo)
    lon = -100.0 + (np.arange(nx) + 2.5) * 0.01
    lat = 40.0 - (np.arange(ny) + 2.5) * 0.01
    lon2d, lat2d = np.meshgrid(lon, lat)
    sza = np.full((ny, nx), 35.0, dtype="float32")
    vza = np.full((ny, nx), 40.0, dtype="float32")
    raa = np.tile(np.linspace(0, 359, nx).astype("float32"), (ny, 1))
    wl = np.array([mcd43.MODIS_CENTRES[b] for b in mcd43.MODIS_BANDS], dtype="float64")
    params = np.broadcast_to(p.values[0, 0], (ny, nx, 7, 3))
    rho = cfactor.model_reflectance(params, sza, vza, raa)
    ds = xr.Dataset(
        {"reflectance": (("y", "x", "wavelength"), rho.astype("float32")),
         "lon": (("y", "x"), lon2d), "lat": (("y", "x"), lat2d),
         "sza": (("y", "x"), sza), "vza": (("y", "x"), vza), "raa": (("y", "x"), raa)},
        coords={"wavelength": wl, "y": np.arange(ny), "x": np.arange(nx)},
        attrs={"sensor": "TEST", "stem": "scene", "datetime": "2023-04-22T19:00:00+0000"})
    return ds, p


def test_model_agreement_recognises_a_matching_shape():
    ds, p = _angular_scene()
    out = cfactor.model_agreement(ds, p, wavelength=858.5, ndvi=None, vza_range=None,
                                  step=30.0, min_count=10)
    assert out["r"] > 0.99
    assert out["r"] > out["r_flipped"]
    assert "matches" in out["verdict"]


def test_model_agreement_catches_an_inverted_azimuth():
    """A scene whose reflectance was built with the opposite convention must be caught."""
    ds, p = _angular_scene()
    ds = ds.copy()
    ds["raa"] = (("y", "x"), ((ds["raa"].values + 180.0) % 360.0).astype("float32"))
    out = cfactor.model_agreement(ds, p, wavelength=858.5, ndvi=None, vza_range=None,
                                  step=30.0, min_count=10)
    assert out["r_flipped"] > out["r"]
    assert "inverted" in out["verdict"]


def test_model_agreement_needs_azimuth_spread():
    ds, p = _scene()                                   # raa takes two values only
    with pytest.raises(ValueError, match="azimuth"):
        cfactor.model_agreement(ds, p, wavelength=858.5, ndvi=None, vza_range=None,
                                step=20.0, min_count=10)


def test_view_profile_ndvi_filter_selects_pixels():
    ds, p = _scene()
    out = cfactor.nbar(ds, params=p, sza_ref="observed", qa_max=None, mask_snow=False, verbose=False)
    wide = cfactor.view_profile(ds, out, wavelength=858.5, step=5.0)
    assert wide["ndvi"] is None and wide["pixels"] > 0
    with pytest.raises(ValueError, match="no valid pixels"):
        cfactor.view_profile(ds, out, wavelength=858.5, step=5.0, ndvi=(0.99, 1.0))


def test_view_profile_refuses_a_fixed_view_angle():
    """DESIS holds the view zenith fixed across a scene; a slope there is meaningless."""
    ds, p = _scene()
    ds = ds.copy()
    ds["vza"] = (("y", "x"), np.full(ds["vza"].shape, 12.74, dtype="float32"))
    out = cfactor.nbar(ds, params=p, qa_max=None, mask_snow=False, verbose=False)
    with pytest.raises(ValueError, match="view zenith"):
        cfactor.view_profile(ds, out, wavelength=858.5, step=0.25)
