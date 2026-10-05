## Capability matrix

| Capability | Release extra / dependencies | What the metadata check cannot prove |
|---|---|---|
| Core read, QA, spatial/spectral, export | numpy, xarray, dask, rasterio, rioxarray, h5py, netCDF4, h5netcdf, scipy, pyproj, shapely, affine, threadpoolctl | Provider siblings, valid transforms, compatible compiled libraries |
| Archive queries/downloads | `search`: earthaccess >=0.11, requests | Credentials, mission approval, connectivity, published granules |
| Notebook map | `search-map`: search, ipyleaflet >=0.17, ipywidgets >=7.6, geopandas | Working widget manager/kernel; static site is not a kernel |
| Atmospheric retrieval | `atmos`: isofit >=4.1,<5 | 6S/emulator/library assets, compilers, usable input, work disk |
| Satellite retrieval of MCD43 | `brdf`: earthengine-api | Earth Engine account/project authorization and suitable parameters |
| Published SRF fetch/read | `srf`: openpyxl, requests | Response URL availability, instrument response validity |
| Notebook execution | `notebooks`: jupyterlab, ipykernel, nbconvert, matplotlib, pandas | Matching kernel environment and scene files |
| Package tests | `test`: pytest >=7 | Provisioned fixtures and independent scientific validation |

Installation guidance is in the [published installation reference](https://fujiangji.github.io/hyperproc/getting-started/installation/); this bundle does not install itself or dependencies. If the user authorizes package changes, preserve their environment policy and version constraints rather than mutating a shared/global environment by default.
