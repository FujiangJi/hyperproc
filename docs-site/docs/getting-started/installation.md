# Installation and environment

The current package declares **Python {{ python_requires }}** and version **{{ source_version }}**. Its installation metadata lives in `pyproject.toml`. Use an isolated environment for processing; the website has its own environment.

## Install this checkout

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows the activate line is `.venv\Scripts\activate` instead. An editable install uses the source you are updating. For a non-editable install of the checkout, use `python -m pip install .`. The README also documents `pip install hyperproc`; these local documentation checks do not verify publication on PyPI.

```python
import hyperproc as hp
print(hp.__version__)
print(hp.__file__)
```

## Requirements

**Python 3.11 or newer.** Developed and tested on **3.12**; 3.13 is declared
and expected to work. 3.14 resolves and installs, but nothing has been run on
it, and `[atmos]` is unlikely to work there until torch and ray catch up.

The Python dependencies do not need installing first. `pip install hyperproc`
brings NumPy, xarray, Dask, rasterio, rioxarray, h5py, netCDF4, h5netcdf,
SciPy, pyproj, Shapely, affine and threadpoolctl with it, in versions it has
resolved together. Installing them by hand beforehand only risks a conflict.

Compiled programs are a different matter: pip cannot supply them, and the
atmospheric engines are built from them on the machine. Only `[atmos]` needs
these.

| Tool | Needed by | Note |
|---|---|---|
| `gfortran`, `make` | every engine, including the default | sRTMnet compiles 6S underneath |
| `gcc`, `gsl` | `--engine LibRadTran` only | take GSL from conda-forge even if the system has one |

```bash
conda create -n hyperproc python=3.12
conda activate hyperproc
conda install -c conda-forge gfortran make gcc gsl
```

The example pipelines under `py_tests/` draw figures and so need matplotlib,
through `'hyperproc[notebooks]'`. The package itself never imports it.

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

### Exact requirements in this checkout

This table is generated from `pyproject.toml` on each build. Constraints listed
here are hyperproc's direct requirements; optional packages can impose further
transitive constraints during installation.

{{ dependency_table }}

## Platforms and atmospheric assets

The package README describes the core as available on Linux, macOS, and Windows, with atmospheric correction on Linux/macOS. A declared platform is separate from a tested dependency/platform matrix.

After installing the atmospheric extra:

```bash
hyperproc-atmos-setup
hyperproc-atmos-setup --check
hyperproc-atmos-setup --engine LibRadTran
```

The third line is optional; it adds the libRadtran engine. Setup downloads several GB of engines and data assets and records their base in ISOFIT's own `~/.isofit/isofit.ini`. The base defaults to `~/.isofit`; pass `--base /data/shared/isofit_assets` to put it somewhere every user of a shared machine can read, so the assets are fetched once. It does not belong inside the package or the environment, which a reinstall would discard. Building 6S needs `gfortran` and `make`; libRadtran needs C/Fortran tooling and GSL. Inspect [configuration and external assets](configuration.md) before running retrievals.

For satellite BRDF downloads, authenticate Earth Engine with `earthengine authenticate` and configure an authorized project. Archive downloads use separate credentials; see [data access](data-access.md).

## When something reports a missing dependency

Two kinds of thing can be missing, and only one of them is a pip install.

**Python packages.** Every optional import raises with the command that
supplies it, so the error message is the instruction:

```text
to_geodataframe needs geopandas:
    pip install 'hyperproc[search-map]'
```

The capability table above lists all of them. An extra always installs
everything that capability needs, so prefer `pip install 'hyperproc[srf]'`
over installing the one package the traceback happened to name first.

**Compilers and libraries.** The radiative-transfer engines are compiled on
the machine, so pip cannot supply these. Which ones you need depends on the
engine, and the default engine needs two of them:

| `--engine` | Needs |
|---|---|
| `sRTMnet` (default) | `gfortran`, `make` - it compiles 6S underneath |
| `6s` | `gfortran`, `make` |
| `LibRadTran` | `gcc`, `gfortran`, `make`, `gsl-config` |

A tool counts when it is on `PATH` or in the running environment's `bin`, so
either a system package or conda-forge works:

```bash
conda install -c conda-forge gfortran make
conda install -c conda-forge gcc gsl
```

Take GSL from conda-forge even if the system has one. The libRadtran build
compiles against the running environment's `include` and `lib`, and ISOFIT's
own build step does not check for GSL - it exits successfully and leaves no
`bin/uvspec` behind.

**Ask before guessing.** `--check` downloads nothing and prints every missing
item with the command that supplies it:

```bash
hyperproc-atmos-setup --check
hyperproc-atmos-setup --check --engine LibRadTran
```

```text
hyperproc.atmos check  (python 3.12.11, isofit 4.1.5)
  ini      /home/you/.isofit/isofit.ini
  gfortran MISSING
  make     /usr/bin/make
  sixs       MISSING  /home/you/.isofit/sixs
  to fix:
    - gfortran: conda install -c conda-forge gfortran   (needed to build the engine)
    - sixs: isofit download sixs   -> /home/you/.isofit/sixs
```

## Building only this website

Install `docs-site/requirements.txt` in a separate environment. API extraction is static and notebooks are rendered from saved outputs. See [maintaining this site](../development/documentation.md).
