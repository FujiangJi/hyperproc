"""Tanager-1 (Planet / Carbon Mapper) reader for the orthorectified products.

Tanager-1 launched in August 2024: 426 bands, 376-2499 nm at 30 m, on a
free-flying smallsat. Planet distributes HDF-EOS5 **grids** rather than swaths,
so the products arrive already map-projected - no GLT, no resampling.

=================  ======  =========================  ====================
file                level   variable                   units
=================  ======  =========================  ====================
``*_ortho_sr_*``    L2A     ``reflectance``            unitless
``*_ortho_radiance_*`` L1B  ``radiance``               W/(m^2 sr um)
=================  ======  =========================  ====================

Three things to know:

1. **Cubes are band-first**, ``(band, y, x)``. Reading them naively transposes
   the image.
2. **Nothing lives in a sidecar** - wavelengths, FWHM, the good-band flag and
   the units are all HDF5 attributes on the cube dataset itself, and the grid
   geometry is in the HDF-EOS ``StructMetadata.0`` text block.
3. **The flagged bands are not a fill value.** 58 of the 426 bands are flagged,
   covering the water-vapour windows from 1342 to 1967 nm. About 76% of those
   values are exactly -0.01 and the rest are failed retrievals scattered from
   -0.24 to 1.38 - so unlike a NaN they all pass ``isfinite`` and read as data.
   ``good_bands_only=True`` blanks them while keeping the band count at 426, so
   indices stay aligned with the sensor's own grid. The radiance product ships
   no ``good_wavelengths`` attribute at all.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from hyperproc.readers._common import datetime_from_id, finish_bands, normalise_angles
import xarray as xr

FILL = -9999.0
GRID = "HDFEOS/GRIDS/HYP"

#: Product tag in the filename -> (level, dataset, variable, long name).
PRODUCTS = {
    "sr": ("L2A", "surface_reflectance", "reflectance", "surface reflectance"),
    "radiance": ("L1B", "toa_radiance", "radiance", "top-of-atmosphere radiance"),
}

#: Per-pixel geometry datasets -> our names.
GEOM = {"sun_zenith": "sza", "sun_azimuth": "saa",
        "sensor_zenith": "vza", "sensor_azimuth": "vaa",
        "sensor_to_ground_path_length": "path_length"}

#: Boolean masks. ``nodata_pixels`` marks cells outside the acquired strip.
MASKS = {"beta_cloud_mask": "cloud", "beta_cirrus_mask": "cirrus",
         "nodata_pixels": "nodata"}

#: Continuous retrievals shipped with the SR product only.
EXTRAS = {"aerosol_optical_depth": "aot", "column_water_vapour": "wv_cm"}

_GRANULE = re.compile(r"^(?P<stem>\d{8}_\d{6}_\d+_\w+)_ortho_(?P<product>sr|radiance)"
                      r"_hdf5\.h5$", re.IGNORECASE)


def open_tanager(
    path: str | Path,
    wl_range: tuple[float, float] | None = None,
    good_bands_only: bool = False,
    masks: bool = True,
    geometry: bool = True,
    extras: bool = True,
    uncertainty: bool = False,
) -> xr.Dataset:
    """Open a Tanager-1 orthorectified granule.

    Args:
        path: ``*_ortho_sr_hdf5.h5`` or ``*_ortho_radiance_hdf5.h5``.
        wl_range: ``(min_nm, max_nm)`` band subset. The sensor covers
            376-2499 nm in 426 bands.
        good_bands_only: set the bands Planet flags unusable to NaN, keeping
            all 426 so band indices stay aligned with the sensor's own grid.
            Roughly 76% of those values are exactly -0.01 and the rest are
            failed retrievals; all of them pass ``isfinite`` and read as real
            data otherwise. **SR only** - the radiance
            product ships no ``good_wavelengths`` attribute.
        masks: attach ``cloud``, ``cirrus`` and ``nodata``.
        geometry: attach per-pixel ``sza``, ``saa``, ``vza``, ``vaa``,
            ``path_length``, plus a derived ``raa``.
        extras: SR only - attach ``aot`` and ``wv_cm``.
        uncertainty: SR only - attach ``reflectance_uncertainty``. Doubles the
            memory, so off by default.

    Returns:
        Dataset with ``reflectance`` or ``radiance`` on ``(y, x, wavelength)``,
        already projected: ``crs`` and ``transform`` come straight from the file.
    """
    import h5py

    path = Path(path)
    m = _GRANULE.match(path.name)
    if m is None:
        raise ValueError(
            f"{path.name} is not a Tanager granule "
            f"(expected <stem>_ortho_<sr|radiance>_hdf5.h5)"
        )
    level, dset, var, long_name = PRODUCTS[m.group("product").lower()]

    with h5py.File(path, "r") as h:
        d = h[f"{GRID}/Data Fields/{dset}"]
        wl = np.asarray(d.attrs["wavelengths"], dtype="float64")
        fwhm = np.asarray(d.attrs["fwhm"], dtype="float64")
        good = (np.asarray(d.attrs["good_wavelengths"]).astype(bool)
                if "good_wavelengths" in d.attrs else None)
        units = str(d.attrs.get("Unit", "")) or "1"

        if good_bands_only and good is None:
            raise ValueError(
                f"good_bands_only=True needs the good_wavelengths attribute, "
                f"which Planet ships on the SR product only. This is the "
                f"{level} {m.group('product')} product."
            )

        keep = np.ones(wl.size, dtype=bool)
        if wl_range is not None:
            keep &= (wl >= wl_range[0]) & (wl <= wl_range[1])
            if not keep.any():
                raise ValueError(f"no Tanager bands in {wl_range[0]}-{wl_range[1]} nm "
                                 f"(sensor covers {wl.min():.0f}-{wl.max():.0f} nm)")
        bi = np.flatnonzero(keep)

        # Lazy through h5netcdf; the file's tiny (14, 42, 49) HDF5 chunks are
        # regrouped into full-width row strips for streaming.
        lazy = xr.open_dataset(path, engine="h5netcdf", group=f"{GRID}/Data Fields",
                               phony_dims="sort", decode_cf=False)
        cube = _lazy_cube(lazy[dset], bi)
        if good_bands_only:
            # Blank in place rather than dropping, so band indices still line up
            # with the sensor's 426. These are failed retrievals, not NaN, so
            # nothing downstream would otherwise notice them.
            cube = cube.where(xr.DataArray(good[keep], dims="wavelength"))

        grid = h[GRID]
        epsg = int(grid.attrs["epsg_code"])
        transform = _geotransform(h, cube.sizes["y"], cube.sizes["x"])

        coords = {"wavelength": ("wavelength", wl[keep]),
                  "fwhm": ("wavelength", fwhm[keep])}
        if good is not None:
            coords["good_wavelength"] = ("wavelength", good[keep])

        ds = xr.Dataset(
            {var: cube},
            coords=coords,
            attrs={
                "sensor": "Tanager", "level": level,
                "granule": path.name.replace("_hdf5.h5", ""),
                "product": m.group("product").lower(),
                "units": units,
                "orthorectified": 1,
                "crs": f"EPSG:{epsg}",
                "transform": transform,
                "strip_id": str(grid.attrs.get("strip_id", "")),
                "created_at": str(grid.attrs.get("created_at", "")),
            },
        )
        ds["wavelength"].attrs.update(units="nm", long_name="band centre")
        ds["fwhm"].attrs.update(units="nm", long_name="band width")
        ds[var].attrs.update(units=units, long_name=long_name)

        ny, nx = ds.sizes["y"], ds.sizes["x"]
        ds.coords["x"] = ("x", transform[0] + (np.arange(nx) + 0.5) * transform[1])
        ds.coords["y"] = ("y", transform[3] + (np.arange(ny) + 0.5) * transform[5])
        ds["x"].attrs.update(units="m", standard_name="projection_x_coordinate")
        ds["y"].attrs.update(units="m", standard_name="projection_y_coordinate")

        fields = h[f"{GRID}/Data Fields"]
        if masks:
            _add_masks(ds, fields)
        if geometry:
            _add_geometry(ds, fields)
        if extras:
            for name, out in EXTRAS.items():
                if name in fields:
                    a = fields[name][:].astype("float32")
                    a[a == FILL] = np.nan
                    ds[out] = (("y", "x"), a)
            if "aot" in ds:
                ds["aot"].attrs["long_name"] = "aerosol optical depth"
            if "wv_cm" in ds:
                ds["wv_cm"].attrs.update(units="cm", long_name="column water vapour")
        if uncertainty and f"{dset}_uncertainty" in fields:
            ds[f"{var}_uncertainty"] = _lazy_cube(lazy[f"{dset}_uncertainty"], bi)
        if "time" in fields:
            t = fields["time"][:].astype("float64")
            t[t == FILL] = np.nan
            ds["acq_time"] = (("y", "x"), t)
            ds["acq_time"].attrs["long_name"] = "per-pixel acquisition time"
    finish_bands(ds, index=bi, fill_value=FILL, datetime=datetime_from_id(ds.attrs["granule"]))
    normalise_angles(ds)
    return ds


def _lazy_cube(raw: xr.DataArray, bi: np.ndarray) -> xr.DataArray:
    """(band, y, x) on disk -> lazy (y, x, wavelength) float32 with FILL as NaN."""
    raw = raw.drop_vars(list(raw.coords), errors="ignore").rename(
        {raw.dims[0]: "wavelength", raw.dims[1]: "y", raw.dims[2]: "x"})
    cube = raw.isel(wavelength=bi).chunk({"wavelength": -1, "y": 168, "x": -1}).astype("float32")
    cube = cube.where(cube != FILL)
    return cube.transpose("y", "x", "wavelength")


def _geotransform(h, ny: int, nx: int):
    """GDAL-order transform from the HDF-EOS StructMetadata text block.

    ``PixelRegistration=HE5_HDFE_CORNER`` with ``GridOrigin=HE5_HDFE_GD_UL``
    means UpperLeftPointMtrs is the outer *edge* of the first pixel, not its
    centre - so it is already the GDAL origin and needs no half-pixel shift.
    """
    sm = h["HDFEOS INFORMATION/StructMetadata.0"][()].decode()
    ul = [float(v) for v in re.search(r"UpperLeftPointMtrs=\(([^)]+)\)", sm).group(1).split(",")]
    lr = [float(v) for v in re.search(r"LowerRightMtrs=\(([^)]+)\)", sm).group(1).split(",")]
    px = (lr[0] - ul[0]) / nx
    py = (ul[1] - lr[1]) / ny
    return (ul[0], px, 0.0, ul[1], 0.0, -py)


def _add_masks(ds: xr.Dataset, fields) -> None:
    for name, out in MASKS.items():
        if name in fields:
            ds[out] = (("y", "x"), fields[name][:] > 0)
            ds[out].attrs["long_name"] = name.replace("_", " ")
    if "nodata" in ds:
        ds["valid"] = (("y", "x"), ~ds["nodata"].values)
        ds["valid"].attrs["long_name"] = "inside the acquired strip"


def _add_geometry(ds: xr.Dataset, fields) -> None:
    for name, out in GEOM.items():
        if name in fields:
            a = fields[name][:].astype("float32")
            a[a == FILL] = np.nan
            ds[out] = (("y", "x"), a)
            if out in ("sza", "saa", "vza", "vaa"):
                ds[out].attrs["units"] = "degrees"
    if "path_length" in ds:
        ds["path_length"].attrs["units"] = "m"
    if "vaa" in ds and "saa" in ds:
        # Derived, as for PACE: the angle BRDF kernels take.
        ds["raa"] = (("y", "x"),
                     np.mod(ds["vaa"].values - ds["saa"].values, 360.0).astype("float32"))
        ds["raa"].attrs.update(units="degrees",
                               long_name="relative azimuth (VAA - SAA, mod 360)")
