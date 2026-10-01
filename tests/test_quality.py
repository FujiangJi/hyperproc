"""The consolidated quality layer: bit semantics, per-sensor folding, masking.

The parts worth testing are the ones a reader cannot check by eye: that a
polarity is applied the right way round, that a coded class map lands on the
flags its lookup table promises, and that nothing is asserted about a pixel
where nothing was observed.
"""
from __future__ import annotations

import numpy as np
import pytest
import xarray as xr

from hyperproc import quality as Q


def _scene(ny=6, nx=8, nwl=5, **layers):
    wl = np.linspace(500, 2400, nwl)
    cube = np.full((ny, nx, nwl), 0.2, dtype="float32")
    ds = xr.Dataset({"reflectance": (("y", "x", "wavelength"), cube)},
                    coords={"wavelength": wl, "y": np.arange(ny), "x": np.arange(nx),
                            "good_wavelength": ("wavelength", np.ones(nwl, bool))},
                    attrs={"sensor": "TEST", "stem": "scene"})
    for name, arr in layers.items():
        ds[name] = (("y", "x"), arr)
    return ds


# --------------------------------------------------------------------------- #
# bit semantics                                                                #
# --------------------------------------------------------------------------- #

def test_flags_are_unique_and_fit_in_uint16():
    assert len(set(Q.FLAGS.values())) == len(Q.FLAGS)
    assert max(Q.FLAGS.values()) <= 15
    assert set(Q.FLAGS) == set(Q.FLAG_DESCRIPTIONS)


def test_layer_is_uint16_with_cf_attributes():
    q = Q.build(_scene(), derive=())
    assert q.dtype == np.uint16
    assert q.name == "quality"
    assert q.attrs["flag_meanings"].split() == list(Q.FLAGS)
    assert [int(m) for m in q.attrs["flag_masks"].split()] == [1 << b for b in Q.FLAGS.values()]


def test_decode_and_set_flag_round_trip():
    q = Q.build(_scene(), derive=())
    assert not Q.decode(q).values.any()
    mask = np.zeros((6, 8), bool); mask[2, 3] = True
    q = Q.set_flag(q, "cloud", mask)
    assert Q.decode(q, "cloud").values[2, 3]
    assert Q.decode(q, "cloud").values.sum() == 1
    assert not Q.decode(q, "water").values.any()
    assert Q.decode(q).values.sum() == 1               # no names = any flag


def test_decode_combines_flags_with_or():
    q = Q.build(_scene(), derive=())
    a = np.zeros((6, 8), bool); a[0, 0] = True
    b = np.zeros((6, 8), bool); b[1, 1] = True
    q = Q.set_flag(Q.set_flag(q, "cloud", a), "water", b)
    assert Q.decode(q, "cloud", "water").values.sum() == 2


def test_unknown_flag_is_refused():
    q = Q.build(_scene(), derive=())
    with pytest.raises(ValueError, match="unknown flag"):
        Q.decode(q, "fog")


def test_build_needs_a_raster():
    with pytest.raises(ValueError, match="y and x"):
        Q.build(xr.Dataset({"a": ("t", [1, 2, 3])}))


# --------------------------------------------------------------------------- #
# folding the providers' own layers                                            #
# --------------------------------------------------------------------------- #

def test_boolean_sources_map_to_their_flags():
    cloud = np.zeros((6, 8), bool); cloud[0, :2] = True
    water = np.zeros((6, 8), bool); water[1, :3] = True
    ds = _scene(cloud=cloud, water=water)
    q = Q.build(ds, derive=())
    assert np.array_equal(Q.decode(q, "cloud").values, cloud)
    assert np.array_equal(Q.decode(q, "water").values, water)


def test_the_many_spellings_of_cloud_all_land_on_one_bit():
    a = np.zeros((6, 8), bool); a[0, 0] = True
    b = np.zeros((6, 8), bool); b[0, 1] = True
    c = np.zeros((6, 8), bool); c[0, 2] = True
    ds = _scene(cloud=a, dilated_cloud=b, cldice=c)
    assert Q.decode(Q.build(ds, derive=()), "cloud").values.sum() == 3


def test_valid_is_inverted_into_fill_but_nodata_is_not():
    valid = np.ones((6, 8), bool); valid[3, 4] = False
    assert Q.decode(Q.build(_scene(valid=valid), derive=()), "fill").values.sum() == 1
    nodata = np.zeros((6, 8), bool); nodata[3, 4] = True
    assert Q.decode(Q.build(_scene(nodata=nodata), derive=()), "fill").values.sum() == 1


def test_land_is_not_inverted_into_water():
    """DESIS flags 10.8 % water but 20.6 % not-land: they are not complements."""
    assert "land" not in Q.BOOLEAN_SOURCES
    land = np.zeros((6, 8), bool)                     # nothing is land
    assert not Q.decode(Q.build(_scene(land=land), derive=()), "water").values.any()


def test_neon_class_map_lands_on_the_documented_flags():
    hcw = np.zeros((6, 8), dtype="uint8")
    hcw[0, 0] = 15   # cloud (land)
    hcw[0, 1] = 7    # snow/ice
    hcw[0, 2] = 21   # topographic shadow
    hcw[0, 3] = 17   # water
    hcw[0, 4] = 1    # shadow
    hcw[0, 5] = 5    # clear land: no flag
    q = Q.build(_scene(hcw_class=hcw), derive=())
    assert Q.decode(q, "cloud").values[0, 0]
    assert Q.decode(q, "snow_ice").values[0, 1]
    assert Q.decode(q, "terrain_shadow").values[0, 2]
    assert Q.decode(q, "water").values[0, 3]
    assert Q.decode(q, "cloud_shadow").values[0, 4]
    assert q.values[0, 5] == 0


def test_prisma_landcover_codes():
    lc = np.full((6, 8), 4, dtype="uint8")            # 4 = forest
    lc[0, 0] = 0                                      # ASI: water
    lc[0, 1] = 1                                      # ASI: snow
    q = Q.build(_scene(landcover=lc), derive=())
    assert Q.decode(q, "water").values[0, 0]
    assert Q.decode(q, "snow_ice").values[0, 1]
    assert q.values[2, 2] == 0


def test_brdf_valid_becomes_brdf_filled_and_fill():
    bv = np.ones((6, 8), dtype="uint8")
    bv[0, 0] = 0                                      # filled, not retrieved
    bv[0, 1] = 2                                      # outside the observation
    q = Q.build(_scene(brdf_valid=bv), derive=())
    assert Q.decode(q, "brdf_filled").values[0, 0]
    assert Q.decode(q, "fill").values[0, 1]
    assert q.values[1, 1] == 0


# --------------------------------------------------------------------------- #
# nothing is claimed where nothing was seen                                    #
# --------------------------------------------------------------------------- #

def test_fill_clears_every_other_flag():
    nodata = np.zeros((6, 8), bool); nodata[0, 0] = True
    cloud = np.zeros((6, 8), bool); cloud[0, 0] = True; cloud[1, 1] = True
    q = Q.build(_scene(nodata=nodata, cloud=cloud), derive=())
    assert q.values[0, 0] == 1 << Q.FLAGS["fill"]      # fill alone
    assert Q.decode(q, "cloud").values[1, 1]           # untouched elsewhere
    assert not Q.decode(q, "cloud").values[0, 0]


# --------------------------------------------------------------------------- #
# derived flags                                                                #
# --------------------------------------------------------------------------- #

def test_fill_derived_from_an_all_nan_spectrum():
    ds = _scene()
    cube = ds["reflectance"].values.copy()
    cube[2, 3, :] = np.nan
    cube[2, 4, 0] = np.nan                             # one band only: still an observation
    ds["reflectance"] = (("y", "x", "wavelength"), cube)
    q = Q.build(ds, derive=("fill",))
    assert Q.decode(q, "fill").values[2, 3]
    assert not Q.decode(q, "fill").values[2, 4]


def test_terrain_shadow_from_cos_i():
    cos_i = np.full((6, 8), 0.5, dtype="float32")
    cos_i[4, 4] = -0.1
    q = Q.build(_scene(cos_i=cos_i), derive=("terrain_shadow",))
    assert Q.decode(q, "terrain_shadow").values.sum() == 1
    assert Q.decode(q, "terrain_shadow").values[4, 4]


def test_steep_terrain_threshold():
    slope = np.full((6, 8), 10.0, dtype="float32")
    slope[1, 1] = 60.0
    q = Q.build(_scene(slope=slope), derive=("steep_terrain",), slope_max=45.0)
    assert Q.decode(q, "steep_terrain").values.sum() == 1


def test_negative_reflectance_needs_many_bands():
    ds = _scene(nwl=10)
    cube = ds["reflectance"].values.copy()
    cube[0, 0, :] = -0.01                              # every band negative
    cube[0, 1, 0] = -0.01                              # one band of ten
    ds["reflectance"] = (("y", "x", "wavelength"), cube)
    q = Q.build(ds, derive=("negative_reflectance",), negative_fraction=0.1)
    assert Q.decode(q, "negative_reflectance").values[0, 0]
    assert not Q.decode(q, "negative_reflectance").values[0, 1]


def test_missing_input_for_a_derived_flag_warns_rather_than_crashes():
    with pytest.warns(UserWarning, match="cos_i"):
        Q.build(_scene(), derive=("terrain_shadow",))


# --------------------------------------------------------------------------- #
# using it                                                                     #
# --------------------------------------------------------------------------- #

def test_apply_masks_the_cube_and_keeps_the_layer():
    cloud = np.zeros((6, 8), bool); cloud[0, 0] = True
    ds = _scene(cloud=cloud)
    out = Q.apply(ds, drop=("cloud",))
    assert np.isnan(out["reflectance"].values[0, 0]).all()
    assert np.isfinite(out["reflectance"].values[1, 1]).all()
    assert "quality" in out
    assert out["reflectance"].attrs["quality_masked"] == "cloud"


def test_apply_leaves_the_input_untouched():
    cloud = np.zeros((6, 8), bool); cloud[0, 0] = True
    ds = _scene(cloud=cloud)
    Q.apply(ds, drop=("cloud",))
    assert np.isfinite(ds["reflectance"].values).all()


def test_summary_fractions_and_clear():
    cloud = np.zeros((6, 8), bool); cloud[0, :4] = True       # 4 of 48
    s = Q.summary(Q.build(_scene(cloud=cloud), derive=()))
    assert s["cloud"] == pytest.approx(4 / 48)
    assert s["clear"] == pytest.approx(44 / 48)
    assert s["water"] == 0.0


def test_describe_lists_every_flag_and_shares():
    q = Q.build(_scene(), derive=())
    plain, withstats = Q.describe(), Q.describe(q)
    for name in Q.FLAGS:
        assert name in plain and name in withstats
    assert "%" in withstats and "%" not in plain
