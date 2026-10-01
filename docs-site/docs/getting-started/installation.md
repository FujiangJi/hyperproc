# Installation and environment

The current package declares **Python {{ python_requires }}** and version **{{ source_version }}**. Its installation metadata lives in `pyproject.toml`. Use an isolated environment for processing; the website has its own environment.

## Install this checkout

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e .
```

An editable install uses the source you are updating. For a non-editable install of the checkout, use `python -m pip install .`. The README also documents `pip install hyperproc`; these local documentation checks do not verify publication on PyPI.

```python
import hyperproc as hp
print(hp.__version__)
print(hp.__file__)
```

## Choose optional capabilities

Use these commands from the repository root. Extras can be combined, for example `'.[search-map,notebooks]'`.

| Capability | Install | Purpose |
|---|---|---|
| Core | `pip install -e .` | Readers, airborne correction, quality, spectral tools, alignment, export |
| Archive access | `pip install -e '.[search]'` | NASA CMR, NEON, and DLR search/download |
| Interactive search map | `pip install -e '.[search-map]'` | Archive access plus ipyleaflet, widgets, and GeoPandas |
| Satellite BRDF | `pip install -e '.[brdf]'` | Earth Engine access for MODIS MCD43 parameters |
| Atmospheric retrieval | `pip install -e '.[atmos]'` | ISOFIT 4.x (`>=4.1,<5`) |
| Response functions | `pip install -e '.[srf]'` | HTTP and spreadsheet support for published SRFs |
| Tutorials | `pip install -e '.[notebooks]'` | JupyterLab, kernel, plotting, and notebook conversion |
| Tests | `pip install -e '.[test]'` | pytest |

The core dependencies include NumPy, xarray, Dask, rasterio, rioxarray, h5py, netCDF4, h5netcdf, SciPy, pyproj, Shapely, affine, and threadpoolctl. See `pyproject.toml` for constraints. ISOFIT introduces its own constraints on h5py/netCDF4 and brings torch and ray.

## Platforms and atmospheric assets

The package README describes the core as available on Linux, macOS, and Windows, with atmospheric correction on Linux/macOS. A declared platform is separate from a tested dependency/platform matrix.

After installing the atmospheric extra:

```bash
hyperproc-atmos-setup --base /path/to/isofit_assets
hyperproc-atmos-setup --check
# Optional libRadtran engine:
hyperproc-atmos-setup --engine LibRadTran
```

Setup downloads several GB of engines and data assets and records the shared base in ISOFIT's configuration. Building 6S needs `gfortran` and `make`; libRadtran needs C/Fortran tooling and GSL. Inspect [configuration and external assets](configuration.md) before running retrievals.

For satellite BRDF downloads, authenticate Earth Engine with `earthengine authenticate` and configure an authorized project. Archive downloads use separate credentials; see [data access](data-access.md).

## Building only this website

Install `docs-site/requirements.txt` in a separate environment. API extraction is static and notebooks are rendered from saved outputs. See [maintaining this site](../development/documentation.md).
