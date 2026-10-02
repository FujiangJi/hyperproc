# Input files and data access

## Find a scene or open an existing delivery

`hp.search()` finds data by sensor, product level, place, and date. `hp.download()` fetches selected results. `hp.open()` reads a local provider product. Follow [search and download](../workflows/search.md) for an end-to-end example and the interactive notebook map.

The current collection table provides **13 searchable sensor/level pairs**:

| Archive | Searchable products | Download credential used by this package |
|---|---|---|
| NASA CMR | EMIT L1B/L2A; PACE L1B/L2; AVIRIS-3 and AVIRIS-5 L1B/L2A | Earthdata `.netrc` or `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` |
| NEON Data API | AOP DP1 flightline reflectance (`NEON`, `L1`) | `NEON_TOKEN` |
| DLR EOC STAC | EnMAP L1B/L1C/L2A; DESIS L2A | Mission-specific username/password |

**Creating the Earthdata credential.** Run this once; it asks for the username
and password and writes `~/.netrc`, after which every run is non-interactive:

```bash
python -c "import earthaccess; earthaccess.login(persist=True)"
```

Configure credentials before starting an unattended run. The CMR downloader
delegates authentication to `earthaccess.login()`, which can prompt when no
usable stored credentials are available. The example pipelines check
`hp.archive.can_download()` before downloading; that preflight checks local
configuration, not the validity of an account or token. The persisted login
above avoids entering credentials for each run.

Searches use anonymous archive access. NEON flightline listing and downloads require a token in this implementation. For DLR, configure `ENMAP_USERNAME`/`ENMAP_PASSWORD` or `DESIS_USERNAME`/`DESIS_PASSWORD`; `DLR_EOC_USERNAME`/`DLR_EOC_PASSWORD` provides a fallback. Mission access is granted separately, so credentials found locally do not establish authorization for both missions.

```python
import hyperproc as hp
print(hp.archive.describe())
print(hp.archive.credentials())  # booleans; does not print secrets
print(hp.archive.can_download("ENMAP", "L2A"))
```

Credential checks inspect local configuration; they do not verify an account against the provider. Registration addresses and missing-credential instructions are included in the backend error messages.

## Preserve the provider delivery

Keep provider filenames and ancillary files next to the primary cube. Most `hp.open()` calls expect a **file**; the AVIRIS route additionally supports directory discovery in documented layouts. Download results can contain a main cube and several siblings: choose the primary product rather than opening the first returned path blindly.

| Reader | Main input | Companion information |
|---|---|---|
| AVIRIS | ENVI cube/header or AVIRIS-5 NetCDF | OBS/geometry, Classic gain/spectral metadata, variant-specific siblings |
| NEON | DP1 reflectance HDF5 | Embedded provider metadata |
| EMIT | L1B RAD or L2A RFL NetCDF | OBS/MASK siblings and GLT information |
| PRISMA | `.he5` product | L2 geometry/geolocation siblings can support L1 |
| EnMAP | Spectral image raster | Matching XML and quality products; L1B detector files |
| DESIS | `SPECTRAL_IMAGE.tif` | Matching metadata XML and quality layers |
| PACE OCI | L1B or L2 SFREFL NetCDF | Corresponding L1B can supply L2 geometry |
| Tanager | Orthorectified radiance/SR HDF5 | Embedded metadata and available ancillary layers |

## Reader support and search coverage

PRISMA, Tanager, AVIRIS-NG, and AVIRIS Classic have readers but no search backend here. DESIS L1B/L1C are readable but not searchable through this package. Unsupported search requests raise an explanation with the alternate archive, rather than returning a misleading empty result. NEON DP3 mosaics have an unimplemented reader route. HISUI, GF-5/AHSI, and Hyperion have no reader in this checkout.

Tutorials use `tests/data/` and saved outputs may reference another machine's paths. Set input/output roots for your own environment. Retain product identifiers, versions, dates, archive, quality documentation, and scaling/geolocation metadata. Store credentials outside notebooks.
