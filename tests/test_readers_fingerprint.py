"""Every reader, against a recorded signature and against physical sense.

Ten thousand lines of this package read files, and the bugs that hurt are the
quiet ones: a band set that shifts by one, a mask whose polarity flips, a
geometry layer that stops being attached, a scale factor applied twice.
Nothing raises. The product simply becomes wrong, and it is noticed weeks
later in a figure.

So each granule on disk is opened and compared two ways.

**Against its own recorded signature** in ``fingerprints.json``: sizes, the
variables and coordinates present, the wavelength grid, the geometry ranges,
and a checksum of a fixed ten-by-ten window of the cube. Any change to any of
those fails, loudly and specifically.

**Against physics**, which no snapshot can drift into accepting: wavelengths
ascend and lie in a plausible range, solar and view zenith stay inside their
hemispheres, reflectance stays near zero to one, radiance stays positive.

The second half matters because a snapshot alone is only as good as the day it
was taken. If a reader was already wrong when the file was written, the
snapshot enshrines the error; the invariants would still catch it.

Regenerating
------------
When a change to a reader is *intended*, rerun the generator in
``scratchpad/fingerprint/make.py`` and read the diff before committing it. A
fingerprint that is regenerated without reading the diff is worse than no test
at all, because it looks like coverage.
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pytest

import hyperproc as hp

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FINGERPRINTS = ROOT / "fingerprints.json"

pytestmark = pytest.mark.data           # deselect with: pytest -m "not data"

#: How each case is opened. Keys match fingerprints.json.
CASES = {
    "EMIT/L1B": ("EMIT/EMIT_L1B_RAD_*.nc", {}),
    "EMIT/L1B/sensor-grid": ("EMIT/EMIT_L1B_RAD_*.nc", {"ortho": False}),
    "EMIT/L2A": ("EMIT/EMIT_L2A_RFL_*.nc", {}),
    "AVIRIS3/L1B": ("AVIRIS3/extracted/AV320231005t181518_L1B_RDN_*_RDN_ORT", {}),
    "AVIRIS3/L2A": ("AVIRIS3/extracted/AV320231005t181518_L2A_OE_*_RFL_ORT", {}),
    "AVIRIS5/L1B": ("AVIRIS5/AV520250508t173511_000_L1B_RDN_*_RDN.nc", {}),
    "AVIRIS5/L2A": ("AVIRIS5/AV520250508t173511_000_L2A_OE_*_RFL_ORT.nc", {}),
    "AVIRIS-NG/L1B": ("AVIRIS_NG/ang20220224t210144_rdn_v2aa1", {}),
    "AVIRIS-NG/L2A": ("AVIRIS_NG/ang20220224t210144_rfl_v2aa1", {}),
    "AVIRIS-CLASSIC/L1B": ("AVIRIS_Classic/f201013t01p00r10rdn_e", {}),
    "AVIRIS-CLASSIC/L2A": ("AVIRIS_Classic/f201013t01p00r10_rfl_v1l1", {}),
    "DESIS/L1B": ("DESIS/DESIS-HSI-L1B-*-SPECTRAL_IMAGE.tif", {}),
    "DESIS/L1C": ("DESIS/DESIS-HSI-L1C-*-SPECTRAL_IMAGE.tif", {}),
    "DESIS/L2A": ("DESIS/DESIS-HSI-L2A-*-SPECTRAL_IMAGE.tif", {}),
    "ENMAP/L1C": ("EnMAP/ENMAP01-____L1C-*-SPECTRAL_IMAGE.TIF", {}),
    "ENMAP/L2A": ("EnMAP/ENMAP01-____L2A-*-SPECTRAL_IMAGE.TIF", {}),
    "NEON/L1": ("NEON_AOP/NEON_D01_BART_DP1_20190825_144302_reflectance.h5", {}),
    "PACE/L1B": ("PACE/PACE_OCI.20260422T195047.L1B.V3.nc", {}),
    "PACE/L2": ("PACE/PACE_OCI.20260422T195047.L2.SFREFL.V3_1.nc", {}),
    "PRISMA/L1": ("PRISMA/PRS_L1_STD_OFFL_*.he5", {}),
    "PRISMA/L2C": ("PRISMA/PRS_L2C_STD_*.he5", {}),
    "PRISMA/L2D": ("PRISMA/PRS_L2D_STD_*.he5", {}),
    "TANAGER/L1B": ("Tanager/*_ortho_radiance_hdf5.h5", {}),
    "TANAGER/L2A": ("Tanager/*_ortho_sr_hdf5.h5", {}),
}

RECORDED = json.loads(FINGERPRINTS.read_text()) if FINGERPRINTS.is_file() else {}


def _digest(a) -> str:
    import hashlib
    return hashlib.md5(np.ascontiguousarray(np.round(np.asarray(a, "float64"), 6))).hexdigest()[:16]


@pytest.fixture(scope="module")
def opened():
    """Open each granule once and share it: some take tens of seconds."""
    warnings.filterwarnings("ignore")
    cache = {}

    def get(key):
        if key not in cache:
            pattern, kw = CASES[key]
            hits = sorted(DATA.glob(pattern))
            if not hits:
                pytest.skip(f"no granule for {key} at {pattern}")
            cache[key] = hp.open(hits[0], **kw)
        return cache[key]
    return get


def _expect(key) -> dict:
    if key not in RECORDED:
        pytest.skip(f"{key} has no recorded fingerprint; run scratchpad/fingerprint/make.py")
    return RECORDED[key]


# --------------------------------------------------------------------------- #
# against the recorded signature                                               #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("key", sorted(CASES))
def test_shape_and_variables_are_unchanged(key, opened):
    want, ds = _expect(key), opened(key)
    assert {k: int(v) for k, v in sorted(ds.sizes.items())} == want["sizes"]
    assert sorted(map(str, ds.data_vars)) == want["data_vars"], "a layer appeared or vanished"
    assert sorted(map(str, ds.coords)) == want["coords"]
    assert hp.main_var(ds) == want["main_var"]


@pytest.mark.parametrize("key", sorted(CASES))
def test_wavelength_grid_is_unchanged(key, opened):
    want, ds = _expect(key), opened(key)
    wl = np.asarray(ds[hp.main_var(ds)]["wavelength"].values, "float64")
    assert wl.size == want["wavelength"]["n"]
    assert float(wl.min()) == pytest.approx(want["wavelength"]["min"], abs=1e-3)
    assert float(wl.max()) == pytest.approx(want["wavelength"]["max"], abs=1e-3)
    assert _digest(wl) == want["wavelength"]["digest"], "the band centres moved"


@pytest.mark.parametrize("key", sorted(CASES))
def test_a_window_of_the_cube_is_unchanged(key, opened):
    """The one that catches a scale factor applied twice, or a band off by one."""
    want, ds = _expect(key), opened(key)
    y0, x0 = want["window"]["origin"]
    win = ds[hp.main_var(ds)].isel(y=slice(y0, y0 + 10), x=slice(x0, x0 + 10)).values
    assert float(np.isfinite(win).mean()) == pytest.approx(want["window"]["finite"], abs=1e-4)
    assert _digest(np.nan_to_num(win, nan=-9999.0)) == want["window"]["digest"], (
        f"the values changed at y={y0}, x={x0}; recorded range {want['window']['range']}, "
        f"now [{np.nanmin(win):.4f}, {np.nanmax(win):.4f}]")


@pytest.mark.parametrize("key", sorted(CASES))
def test_geometry_layers_are_unchanged(key, opened):
    want, ds = _expect(key), opened(key)
    for name, expected in want["geometry"].items():
        assert name in ds, f"{name} is no longer attached"
        if expected is None:
            continue
        got = np.asarray(ds[name].values)
        step = int(np.ceil(np.sqrt(got.size / 1_000_000))) if got.size > 1_000_000 else 1
        sample = got[::step, ::step] if got.ndim == 2 else got[::step]
        finite = np.asarray(sample, "float64")[np.isfinite(sample)]
        assert finite.size, f"{name} became all NaN"
        assert float(finite.min()) == pytest.approx(expected[0], abs=1e-3)
        assert float(finite.max()) == pytest.approx(expected[1], abs=1e-3)


@pytest.mark.parametrize("key", sorted(CASES))
def test_attributes_are_unchanged(key, opened):
    want, ds = _expect(key), opened(key)
    for name, expected in want["attrs"].items():
        assert str(ds.attrs.get(name, "")) == expected, f"attrs[{name!r}] changed"
    assert str(ds.attrs.get("crs", "")) == want["crs"]


# --------------------------------------------------------------------------- #
# against physics, which a snapshot cannot drift into accepting                #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("key", sorted(CASES))
def test_wavelengths_ascend_and_are_plausible(key, opened):
    ds = opened(key)
    wl = np.asarray(ds[hp.main_var(ds)]["wavelength"].values, "float64")
    assert np.all(np.diff(wl) > 0), "band centres must ascend; sort them in the reader"
    assert 300 < wl.min() < 700 and 900 < wl.max() < 2600
    if "fwhm" in ds.coords:
        fwhm = np.asarray(ds["fwhm"].values, "float64")
        assert np.all(fwhm[np.isfinite(fwhm)] > 0)


@pytest.mark.parametrize("key", sorted(CASES))
def test_angles_stay_inside_their_hemispheres(key, opened):
    ds = opened(key)
    limits = {"sza": (0, 90), "vza": (0, 90), "saa": (0, 360), "vaa": (0, 360), "raa": (0, 360)}
    for name, (lo, hi) in limits.items():
        if name not in ds:
            continue
        a = np.asarray(ds[name].values)
        step = int(np.ceil(np.sqrt(a.size / 1_000_000))) if a.size > 1_000_000 else 1
        s = np.asarray(a[::step, ::step] if a.ndim == 2 else a[::step], "float64")
        f = s[np.isfinite(s)]
        if not f.size:
            continue
        assert f.min() >= lo - 1e-6 and f.max() <= hi + 1e-6, \
            f"{name} spans {f.min():.2f}..{f.max():.2f}, outside [{lo}, {hi}]"


@pytest.mark.parametrize("key", sorted(CASES))
def test_values_are_physically_plausible(key, opened):
    """Reflectance near zero to one; radiance positive. Catches a scale factor.

    Read from the data rather than from the recorded fingerprint: an invariant
    that is asserted against a snapshot is only as true as the day it was
    taken, and this one has to stay true forever.

    Restricted to the bands the reader flags usable, because the flag is the
    package's own contract. JPL's AVIRIS Classic reflectance reaches +/-451 in
    the water-vapour bands at 1373 and 1861 nm; those are flagged unusable and
    the same spectrum sits between -0.02 and 0.22 everywhere else. Checking a
    band the reader tells you to ignore would raise a false alarm about the
    provider's data, not ours.
    """
    want, ds = _expect(key), opened(key)
    y0, x0 = want["window"]["origin"]
    var = hp.main_var(ds)
    win = ds[var].isel(y=slice(y0, y0 + 10), x=slice(x0, x0 + 10)).values
    if "good_wavelength" in ds.coords:
        good = np.asarray(ds["good_wavelength"].values, bool)
        if good.any():
            win = win[..., good]
    finite = win[np.isfinite(win)]
    assert finite.size, "the window is entirely NaN; the fingerprint would check nothing"
    # On a percentile, not the extremes. JPL's Classic product carries isolated spikes on
    # the shoulder of the water band (two values in 19 400 reach +453 at 1323 nm), and
    # those are the provider's, not ours. A scale factor applied twice moves the whole
    # distribution, which a percentile catches and an outlier test would drown in noise.
    lo, hi = (float(v) for v in np.percentile(finite, [1, 99]))
    extremes = f"(extremes {finite.min():.3g} .. {finite.max():.3g})"
    units = str(ds.attrs.get("units", "")).lower()
    reflectance = units in ("1", "unitless", "") or "reflect" in units
    if reflectance:
        assert -0.5 < lo and hi < 2.0, \
            f"reflectance p1-p99 outside [-0.5, 2] in good bands: {lo:.4g} .. {hi:.4g} {extremes}"
    else:
        assert hi > 0, f"radiance should be positive somewhere: {lo:.4g} .. {hi:.4g} {extremes}"
        assert lo > -1.0, f"radiance well below zero: {lo:.4g} {extremes}"


@pytest.mark.parametrize("key", sorted(CASES))
def test_a_projected_product_can_be_written(key, opened):
    """The grid is only right if it survives the writer; this is the io half."""
    ds = opened(key)
    if not ds.attrs.get("crs"):
        pytest.skip("not projected; georeference() first")
    from hyperproc.io import _transform_for
    affine = _transform_for(ds)
    assert affine is not None and affine.a != 0 and affine.e != 0
    y0, x0 = _expect(key)["window"]["origin"]
    sub = ds.isel(y=slice(y0, y0 + 10), x=slice(x0, x0 + 10))
    sub_affine = _transform_for(sub)
    assert sub_affine is not None
    # The general affine, not a north-up one: on a flight-aligned AVIRIS grid the rotation
    # terms are non-zero, so easting depends on the row as well as the column. Assuming
    # otherwise is what puts a rotated subset in the wrong place.
    assert (sub_affine.a, sub_affine.b, sub_affine.d, sub_affine.e) == \
        pytest.approx((affine.a, affine.b, affine.d, affine.e), rel=1e-9)
    scale = max(abs(affine.a), abs(affine.e)) * 0.01
    assert sub_affine.c == pytest.approx(affine.c + x0 * affine.a + y0 * affine.b, abs=scale)
    assert sub_affine.f == pytest.approx(affine.f + x0 * affine.d + y0 * affine.e, abs=scale)


# --------------------------------------------------------------------------- #
# DLR's cloud-optimised spelling                                              #
# --------------------------------------------------------------------------- #

def test_an_enmap_granule_named_the_way_dlrs_catalogue_names_it_opens(tmp_path):
    """The STAC catalogue links ``*_COG.TIF``; the order form delivers
    ``*.TIF``. hyperproc.search downloads the first, so the reader has to open
    it, find its ``_COG`` siblings, and produce the same cube."""
    plain = sorted(DATA.glob("EnMAP/ENMAP01-____L2A-*-SPECTRAL_IMAGE.TIF"))
    if not plain:
        pytest.skip("no EnMAP L2A granule in tests/data")
    stem = plain[0].name.replace("-SPECTRAL_IMAGE.TIF", "")

    for src in DATA.glob(f"EnMAP/{stem}*"):
        name = src.name
        if name.endswith(".TIF"):
            name = name[: -len(".TIF")] + "_COG.TIF"
        (tmp_path / name).symlink_to(src)

    cog = tmp_path / f"{stem}-SPECTRAL_IMAGE_COG.TIF"
    assert hp.sniff(cog.name) == ("ENMAP", "L2A")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        a = hp.open(plain[0], pixelmask=True)
        b = hp.open(cog, pixelmask=True)

    assert set(a.data_vars) == set(b.data_vars), "the _COG siblings were all found"
    assert a.sizes == b.sizes
    np.testing.assert_array_equal(a.wavelength.values, b.wavelength.values)
    np.testing.assert_array_equal(a.reflectance[::100, ::100, ::40].values,
                                  b.reflectance[::100, ::100, ::40].values)
    np.testing.assert_array_equal(a.cloud.values, b.cloud.values)
