"""Coregistration: does it recover a shift we put there on purpose?

Every test here plants a known offset and asks for it back. That is the only
honest way to test a matcher: a correlation peak always exists, so the
question is never "did it find something" but "did it find the right thing,
and did it say so when there was nothing to find".
"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from hyperproc import align as A


def _scene(field, res=30.0, x0=500000.0, y0=4600000.0, crs="EPSG:32610", nwl=5):
    """A projected dataset whose single band is ``field``."""
    ny, nx = field.shape
    cube = np.repeat(np.asarray(field, dtype="float32")[:, :, None], nwl, axis=2)
    return xr.Dataset(
        {"reflectance": (("y", "x", "wavelength"), cube)},
        coords={"wavelength": np.linspace(600, 1000, nwl),
                "x": x0 + (np.arange(nx) + 0.5) * res,
                "y": y0 - (np.arange(ny) + 0.5) * res},
        attrs={"sensor": "TEST", "stem": "scene", "crs": crs,
               "transform": (x0, res, 0.0, y0, 0.0, -res)})


def _texture(ny=128, nx=128, seed=0, smooth=3.0):
    """A random but spatially smooth field: something a matcher can lock onto."""
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal((ny, nx)), smooth)
    f -= f.min()
    return (f / f.max() * 0.4 + 0.05).astype("float32")


def _shifted(field, dy, dx):
    from scipy.ndimage import shift as ndshift
    return ndshift(field, (dy, dx), order=3, mode="nearest").astype("float32")


# --------------------------------------------------------------------------- #
# measuring                                                                    #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("dy,dx", [(0, 0), (3, -5), (-7, 2), (11, 9)])
def test_a_whole_pixel_shift_is_recovered(dy, dx):
    ref = _texture()
    moving = _scene(_shifted(ref, -dy, -dx))       # content displaced the other way
    fit = A.estimate_shift(moving, _scene(ref), tiles=0)
    assert fit["dy"] == pytest.approx(dy, abs=0.3)
    assert fit["dx"] == pytest.approx(dx, abs=0.3)
    assert fit["snr"] > 3.0


def test_a_subpixel_shift_is_recovered():
    ref = _texture(seed=1)
    moving = _scene(_shifted(ref, -2.4, 1.7))
    fit = A.estimate_shift(moving, _scene(ref), tiles=0)
    assert fit["dy"] == pytest.approx(2.4, abs=0.35)
    assert fit["dx"] == pytest.approx(-1.7, abs=0.35)


def test_the_shift_is_reported_in_map_units_too():
    ref = _texture(seed=2)
    moving = _scene(_shifted(ref, -4, 0), res=30.0)
    fit = A.estimate_shift(moving, _scene(ref, res=30.0), tiles=0)
    assert fit["dy_m"] == pytest.approx(fit["dy"] * 30.0)
    assert fit["resolution"] == (30.0, 30.0)


def test_unrelated_scenes_are_not_called_consistent():
    a, b = _texture(seed=3), _texture(seed=99)
    fit = A.estimate_shift(_scene(a), _scene(b), tiles=4, min_snr=8.0)
    assert not fit["consistent"]
    assert "NOT consistent" in fit["report"]


def test_tiles_agree_on_a_real_shift_and_are_counted():
    ref = _texture(ny=160, nx=160, seed=4)
    moving = _scene(_shifted(ref, -5, 3))
    fit = A.estimate_shift(moving, _scene(ref), tiles=4)
    assert fit["tiles_kept"] >= 3
    assert fit["scatter"] < 1.0
    assert fit["consistent"]


def test_tiles_too_small_to_match_are_refused():
    ref = _texture(ny=40, nx=40, seed=5)
    with pytest.raises(ValueError, match="too small to match"):
        A.tie_points(_scene(ref), _scene(ref), tiles=8)


def test_non_overlapping_scenes_are_caught():
    ref = _texture(seed=6)
    far = _scene(_texture(seed=7), x0=900000.0, y0=3000000.0)
    with pytest.raises(ValueError, match="do not appear to overlap"):
        A.estimate_shift(far, _scene(ref), tiles=0)


def test_an_unprojected_dataset_is_refused():
    ds = _scene(_texture(seed=8))
    ds.attrs.pop("crs")
    with pytest.raises(ValueError, match="no CRS"):
        A.estimate_shift(ds, _scene(_texture(seed=8)), tiles=0)


def test_a_brightness_difference_does_not_move_the_answer():
    """Phase correlation uses phase, not amplitude: that is why it works across sensors."""
    ref = _texture(seed=10)
    moving = _scene(_shifted(ref, -4, 6) * 2.5 + 0.1)      # gain and offset
    fit = A.estimate_shift(moving, _scene(ref), tiles=0)
    assert fit["dy"] == pytest.approx(4, abs=0.3)
    assert fit["dx"] == pytest.approx(-6, abs=0.3)


# --------------------------------------------------------------------------- #
# correcting                                                                   #
# --------------------------------------------------------------------------- #

def test_apply_shift_moves_the_georeferencing_and_nothing_else():
    """Content moving down and right means its coordinates gain x and lose y."""
    ds = _scene(_texture(seed=11), res=30.0)
    out = A.apply_shift(ds, dy=2.0, dx=-3.0)
    assert np.allclose(out["x"].values, ds["x"].values - 3.0 * 30.0)
    assert np.allclose(out["y"].values, ds["y"].values - 2.0 * 30.0)
    assert np.array_equal(out["reflectance"].values, ds["reflectance"].values)
    assert out.attrs["transform"][0] == pytest.approx(ds.attrs["transform"][0] - 90.0)
    assert out.attrs["transform"][3] == pytest.approx(ds.attrs["transform"][3] - 60.0)


def test_apply_shift_accepts_map_units():
    ds = _scene(_texture(seed=12), res=30.0)
    a = A.apply_shift(ds, dy=1.0, dx=1.0, unit="pixel")
    b = A.apply_shift(ds, dy=30.0, dx=30.0, unit="map")
    assert np.allclose(a["x"].values, b["x"].values)
    with pytest.raises(ValueError, match="unit must be"):
        A.apply_shift(ds, 1.0, 1.0, unit="metres")


def test_coregister_removes_the_shift_it_measured():
    ref_field = _texture(ny=160, nx=160, seed=13)
    reference = _scene(ref_field)
    moving = _scene(_shifted(ref_field, -6, 4))
    fixed = A.coregister(moving, reference, verbose=False)
    again = A.estimate_shift(fixed, reference, tiles=0)
    assert abs(again["dy"]) < 0.4 and abs(again["dx"]) < 0.4
    assert "aligned to" in fixed.attrs["coregistration"]


def test_coregister_refuses_an_inconsistent_match():
    a, b = _texture(seed=14), _texture(seed=77)
    with pytest.raises(ValueError, match="did not match consistently"):
        A.coregister(_scene(a), _scene(b), min_snr=8.0, verbose=False)


def test_coregister_can_be_forced():
    a, b = _texture(seed=15), _texture(seed=88)
    out = A.coregister(_scene(a), _scene(b), min_snr=8.0, force=True, verbose=False)
    assert "aligned to" in out.attrs["coregistration"]


def test_partial_overlap_is_matched_on_the_common_area():
    """Two sensors rarely cover the same ground; the NaN elsewhere must not win."""
    big = _texture(ny=200, nx=200, seed=20)
    reference = _scene(big)
    part = _scene(_shifted(big, -4, 3)[:120, :120])           # covers the top-left corner only
    fit = A.estimate_shift(part, reference, tiles=0)
    assert fit["dy"] == pytest.approx(4, abs=0.4)
    assert fit["dx"] == pytest.approx(-3, abs=0.4)


def test_resample_puts_the_cube_on_the_reference_grid():
    ref_field = _texture(ny=160, nx=160, seed=16)
    reference = _scene(ref_field)
    coarse = _shifted(ref_field, -6, 4)[::2, ::2]             # half the pixels, twice the size
    moving = _scene(coarse, res=60.0)                        # a coarser sensor, same ground
    out = A.coregister(moving, reference, resample=True, verbose=False)
    assert out.sizes["y"] == reference.sizes["y"] and out.sizes["x"] == reference.sizes["x"]
    assert np.allclose(out["x"].values, reference["x"].values)
    assert out.sizes["wavelength"] == moving.sizes["wavelength"]
    assert "resampled to the reference grid" in out.attrs["coregistration"]


def test_report_is_readable():
    ref = _texture(ny=160, nx=160, seed=17)
    fit = A.estimate_shift(_scene(_shifted(ref, -2, 2)), _scene(ref), tiles=4)
    for word in ("shift", "peak", "tiles", "verdict"):
        assert word in fit["report"]


def test_a_projected_shift_is_already_in_metres():
    ref = _texture(seed=30)
    fit = A.estimate_shift(_scene(_shifted(ref, -4, 0), res=30.0), _scene(ref, res=30.0), tiles=0)
    assert fit["dy_metres"] == pytest.approx(fit["dy"] * 30.0, rel=1e-6)


def test_a_geographic_shift_is_converted_to_metres():
    """EMIT is in degrees: a report of "0.0 degrees" would tell nobody anything."""
    ref = _texture(seed=31)
    kw = dict(res=0.000542, x0=-121.0, y0=35.0, crs="EPSG:4326")
    fit = A.estimate_shift(_scene(_shifted(ref, -5, 0), **kw), _scene(ref, **kw), tiles=0)
    assert fit["dy_metres"] == pytest.approx(5 * 0.000542 * 111320.0, rel=0.05)
    assert 250 < fit["dy_metres"] < 350                 # five EMIT pixels, about 300 m
    assert " m," in fit["report"] and "m on the ground" in fit["report"]


def test_resample_reads_the_cube_one_band_at_a_time():
    """A full scene would need gigabytes if the cube were materialised first."""
    ref_field = _texture(ny=64, nx=64, seed=40)
    reference = _scene(ref_field)
    moving = _scene(_shifted(ref_field, -2, 1), nwl=9).chunk({"wavelength": 1})
    assert moving["reflectance"].chunks is not None
    out = A.coregister(moving, reference, resample=True, tiles=0, verbose=False)
    assert out.sizes == {"y": 64, "x": 64, "wavelength": 9}
    assert np.isfinite(out["reflectance"].values).any()
