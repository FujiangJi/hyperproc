# Choose only the necessary capabilities

Core includes provider readers, airborne topographic/FlexBRDF algorithms, QA, spectral tools, alignment and raster exports. Its direct requirements are in the release manifest; installed metadata and `python -m pip check` determine actual compatibility.

| Extra | Needed for |
|---|---|
| `search` | NASA CMR, NEON, DLR search/download |
| `search-map` | Search plus ipyleaflet/ipywidgets/geopandas notebook map |
| `srf` | Fetch/read published agency spectral-response spreadsheets |
| `brdf` | Earth Engine-backed MCD43 fetch for satellite NBAR; not required merely to fit airborne BRDF |
| `atmos` | ISOFIT >=4.1,<5 Python package; external engine/data assets separate |
| `notebooks` | JupyterLab, kernel, plotting and notebook conversion |
| `test` | pytest for package regression tests |

Portable double-quoted pip examples:

```bash
python -m pip install "hyperproc[search,srf]==0.1.2"
python -m pip install "hyperproc[atmos,brdf,notebooks]==0.1.2"
python -m pip check
```

Choose an example matching the task; the second is not a default requirement for one index. `search-map` includes `search`; ordinary smoothing and explicit-target resampling do not need `srf`. Search-map needs a working notebook widget manager/kernel; static website saved maps do not execute Python queries.

ISOFIT introduces its own Python, h5py/netCDF4, torch/Ray constraints. Do not manually defeat the resolver's upper bounds to fit an already inconsistent environment. For the reviewed ISOFIT 4.1.5, use Python >=3.11,<3.13; verify the actual installed distribution for future releases. Successful pip installation does not validate engines, credentials, data or scientific suitability.

Earth Engine needs separate authentication/project authorization. NASA Earthdata, NEON and DLR credentials are unrelated to Earth Engine. Availability checks are booleans, not provider authentication proof. See [acquisition](../operations/acquisition.md).

After a user-approved dependency change, rerun [verification](verification.md) in the same environment and record the exact resolved versions rather than assuming the extra name proves readiness.
