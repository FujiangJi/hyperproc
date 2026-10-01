"""ENVI output: the header, the round trip, and that GeoTIFF is unchanged.

The reason to write ENVI rather than GeoTIFF is the header. A GeoTIFF can only
label a band with free text, so ``650.4 nm`` is something a human reads; an
ENVI header states ``wavelength``, ``fwhm`` and ``bbl`` as fields that come
back as numbers. So most of these tests are about the header being right, and
the rest are about the pixels surviving unchanged.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
import xarray as xr

import hyperproc as hp
from hyperproc.io import FORMATS, envi_header


def _cube(ny=6, nx=8, nwl=12, crs="EPSG:32610", res=30.0, x0=500000.0, y0=4600000.0,
          fwhm=True, good=True, stem="scene"):
    wl = np.linspace(400.123456, 2400.987654, nwl)
    rng = np.random.default_rng(0)
    data = rng.uniform(0.01, 0.6, (ny, nx, nwl)).astype("float32")
    coords = {"wavelength": wl, "y": y0 - (np.arange(ny) + 0.5) * res,
              "x": x0 + (np.arange(nx) + 0.5) * res}
    if fwhm:
        coords["fwhm"] = ("wavelength", np.full(nwl, 8.4159))
    if good:
        flags = np.ones(nwl, bool)
        flags[nwl // 3:nwl // 3 + 2] = False
        coords["good_wavelength"] = ("wavelength", flags)
    return xr.Dataset({"reflectance": (("y", "x", "wavelength"), data)}, coords=coords,
                      attrs={"sensor": "TEST", "level": "L2A", "granule": stem, "stem": stem,
                             "units": "1", "crs": crs,
                             "transform": (x0, res, 0.0, y0, 0.0, -res)})


def _hdr_fields(path: Path) -> dict:
    with rasterio.open(path) as src:
        return src.tags(ns="ENVI")


# --------------------------------------------------------------------------- #
# the header fields                                                            #
# --------------------------------------------------------------------------- #

def test_envi_header_lists_wavelengths_fwhm_and_bad_bands():
    ds = _cube()
    fields = envi_header(ds)
    assert set(fields) == {"wavelength", "wavelength units", "fwhm", "bbl"}
    assert fields["wavelength units"] == "Nanometers"
    wl = [float(v) for v in fields["wavelength"].strip("{}").split(",")]
    assert np.allclose(wl, ds.wavelength.values, atol=1e-6)
    bbl = [int(v) for v in fields["bbl"].strip("{}").split(",")]
    assert np.array_equal(np.array(bbl, bool), ds.good_wavelength.values)
    assert sum(bbl) == int(ds.good_wavelength.values.sum())


def test_envi_header_omits_what_the_dataset_lacks():
    assert "fwhm" not in envi_header(_cube(fwhm=False))
    assert "bbl" not in envi_header(_cube(good=False))
    assert envi_header(xr.Dataset()) == {}


def test_wavelengths_survive_to_better_than_a_thousandth_of_a_nanometre(tmp_path):
    """Six significant digits, the obvious choice, loses 5e-3 nm on EMIT."""
    ds = _cube()
    p = hp.to_envi(ds, tmp_path / "cube.img")
    wl = np.array([float(v) for v in _hdr_fields(p)["wavelength"].strip("{}").split(",")])
    assert np.abs(wl - ds.wavelength.values).max() < 1e-3


def test_bbl_uses_envis_convention_of_one_for_good(tmp_path):
    ds = _cube()
    p = hp.to_envi(ds, tmp_path / "cube.img")
    bbl = np.array([int(v) for v in _hdr_fields(p)["bbl"].strip("{}").split(",")], bool)
    assert np.array_equal(bbl, ds.good_wavelength.values)
    assert not bbl.all(), "the fixture has bad bands, so this must not be all ones"


# --------------------------------------------------------------------------- #
# the round trip                                                               #
# --------------------------------------------------------------------------- #

def test_pixels_and_grid_survive(tmp_path):
    ds = _cube()
    p = hp.to_envi(ds, tmp_path / "cube.img")
    assert p.with_suffix(".hdr").is_file()
    with rasterio.open(p) as src:
        assert src.count == ds.sizes["wavelength"]
        assert (src.height, src.width) == (ds.sizes["y"], ds.sizes["x"])
        assert str(src.crs) == ds.attrs["crs"]
        assert np.array_equal(src.read(), ds.reflectance.transpose("wavelength", "y", "x").values)
        # the header is text, so the transform survives to its printed precision
        want = hp.io._transform_for(ds)
        assert max(abs(a - b) for a, b in zip(tuple(src.transform)[:6], tuple(want)[:6])) < 1e-9


def test_band_descriptions_are_written_too(tmp_path):
    ds = _cube()
    with rasterio.open(hp.to_envi(ds, tmp_path / "cube.img")) as src:
        assert src.descriptions[0].endswith(" nm")
        assert float(src.descriptions[0].split()[0]) == pytest.approx(ds.wavelength.values[0], abs=0.1)


@pytest.mark.parametrize("interleave", ["bil", "bip", "bsq"])
def test_every_interleave_round_trips(tmp_path, interleave):
    ds = _cube()
    p = hp.to_envi(ds, tmp_path / f"{interleave}.img", interleave=interleave)
    assert _hdr_fields(p)["interleave"] == interleave
    with rasterio.open(p) as src:
        assert np.array_equal(src.read(), ds.reflectance.transpose("wavelength", "y", "x").values)


def test_an_unknown_interleave_is_refused(tmp_path):
    with pytest.raises(ValueError, match="interleave must be"):
        hp.to_envi(_cube(), tmp_path / "x.img", interleave="bqs")


def test_the_dask_path_gives_the_same_file(tmp_path):
    ds = _cube(ny=40, nx=12, nwl=20)
    a = hp.to_envi(ds, tmp_path / "plain.img")
    b = hp.to_envi(ds.chunk({"y": 7}), tmp_path / "chunked.img")
    assert a.read_bytes() == b.read_bytes()


def test_a_directory_names_the_file_with_the_right_extension(tmp_path):
    ds = _cube(stem="GRANULE_X")
    assert hp.to_envi(ds, tmp_path).name == "GRANULE_X.img"
    assert hp.to_geotiff(ds, tmp_path).name == "GRANULE_X.tif"


def test_a_stem_containing_dots_still_finds_its_header(tmp_path):
    """PACE ids carry dots; the ISOFIT layer had to special-case exactly this."""
    ds = _cube(stem="PACE_OCI.20260422T195047.L1B.V3_ac")
    p = hp.to_envi(ds, tmp_path)
    assert p.name.endswith(".img")
    assert p.with_suffix(".hdr").is_file(), sorted(x.name for x in tmp_path.iterdir())


def test_a_sensor_grid_cube_is_refused(tmp_path):
    ds = _cube()
    del ds.attrs["crs"]
    with pytest.raises(ValueError, match="no CRS"):
        hp.to_envi(ds, tmp_path / "x.img")


# --------------------------------------------------------------------------- #
# choosing between the two                                                     #
# --------------------------------------------------------------------------- #

def test_to_raster_dispatches(tmp_path):
    ds = _cube()
    assert hp.to_raster(ds, tmp_path / "a.tif", format="GTiff").suffix == ".tif"
    assert hp.to_raster(ds, tmp_path / "b.img", format="ENVI").suffix == ".img"
    with pytest.raises(ValueError, match="format must be one of"):
        hp.to_raster(ds, tmp_path / "c", format="JP2")


def test_formats_table_is_the_single_source_of_extensions():
    assert FORMATS == {"GTiff": ".tif", "ENVI": ".img"}


def test_geotiff_still_behaves_as_before(tmp_path):
    """The refactor must not have moved the GeoTIFF path."""
    ds = _cube()
    p = hp.to_geotiff(ds, tmp_path / "cube.tif", overviews=[2])
    with rasterio.open(p) as src:
        assert src.driver == "GTiff"
        assert src.count == ds.sizes["wavelength"]
        assert src.overviews(1) == [2]
        assert np.allclose(src.read(), ds.reflectance.transpose("wavelength", "y", "x").values)


def test_envi_warns_rather_than_failing_when_asked_for_overviews(tmp_path):
    ds = _cube()
    ds["aot"] = (("y", "x"), np.full((ds.sizes["y"], ds.sizes["x"]), 0.2, dtype="float32"))
    with pytest.warns(UserWarning, match="no internal pyramids"):
        p = hp.to_geotiff_2d(ds, tmp_path / "aot.img", var="aot", format="ENVI", overviews=True)
    with rasterio.open(p) as src:
        assert src.driver == "ENVI" and src.overviews(1) == []


def test_a_two_dimensional_layer_writes_in_either_format(tmp_path):
    ds = _cube()
    ds["quality"] = (("y", "x"), np.arange(ds.sizes["y"] * ds.sizes["x"],
                                           dtype="uint16").reshape(ds.sizes["y"], ds.sizes["x"]))
    a = hp.to_geotiff_2d(ds, tmp_path / "q.tif", var="quality")
    b = hp.to_geotiff_2d(ds, tmp_path / "q.img", var="quality", format="ENVI")
    with rasterio.open(a) as sa, rasterio.open(b) as sb:
        assert sa.dtypes[0] == sb.dtypes[0] == "uint16"
        assert np.array_equal(sa.read(1), sb.read(1))


# --------------------------------------------------------------------------- #
# on a real granule                                                            #
# --------------------------------------------------------------------------- #

@pytest.mark.data
def test_a_real_emit_window_round_trips():
    data = Path(__file__).resolve().parent / "data" / "EMIT"
    hits = sorted(data.glob("EMIT_L2A_RFL_*.nc"))
    if not hits:
        pytest.skip("no EMIT granule")
    import tempfile
    ds = hp.open(hits[0]).isel(y=slice(800, 830), x=slice(800, 830))   # inside the swath
    with tempfile.TemporaryDirectory() as tmp:
        p = hp.to_envi(ds, Path(tmp) / "emit.img")
        with rasterio.open(p) as src:
            want = ds.reflectance.transpose("wavelength", "y", "x").values
            assert np.isfinite(want).any(), "pick a window inside the swath"
            assert np.array_equal(src.read(), want, equal_nan=True)
            tags = src.tags(ns="ENVI")
        wl = np.array([float(v) for v in tags["wavelength"].strip("{}").split(",")])
        assert np.abs(wl - ds.wavelength.values).max() < 1e-3
        bbl = np.array([int(v) for v in tags["bbl"].strip("{}").split(",")], bool)
        assert np.array_equal(bbl, ds.good_wavelength.values)
        assert bbl.sum() == 244, "EMIT ships 244 usable bands of 285"


def test_scene_metadata_lands_in_the_header_not_a_sidecar(tmp_path):
    """Written to GDAL's default domain it would go to a .aux.xml ENVI cannot read."""
    ds = _cube()
    p = hp.to_envi(ds, tmp_path / "cube.img")
    text = p.with_suffix(".hdr").read_text()
    for key, value in (("sensor", "TEST"), ("level", "L2A"), ("granule", "scene"),
                       ("units", "1"), ("variable", "reflectance")):
        assert f"{key} = {value}" in text, f"{key} missing from the header"
