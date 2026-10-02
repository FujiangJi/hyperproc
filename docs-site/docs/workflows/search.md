# Search and download granules

Start from a place and date with `hyperproc.archive`, then hand the downloaded provider product to the existing reader workflow. Install the `search` extra; the notebook map additionally needs `search-map`.

## Search without downloading

```python
import hyperproc as hp

hits = hp.search(
    "EMIT", "L2A",
    bbox=(-121.0, 34.0, -119.8, 35.1),  # west, south, east, north
    date=("2023-04-20", "2023-04-25"),
    count=5,
)
print(hits)
for granule in hits:
    print(granule.name, granule.time, granule.size_mb, granule.browse)
```

All backends return `Results` containing `Granule` records with sensor, level, collection, acquisition time, bounding box, download links, and provider metadata in `raw`. Size, cloud fraction, or public quicklook may be unavailable. Use `count` to bound results; `count=-1` requests all matches.

`cloud=(min, max)` is a percentage filter only for collections that publish it. PACE L1B, NEON, and the AVIRIS collections do not support it. CMR also accepts `version=`; default searches do not pin one version. NEON accepts `site=` and `site_radius_km=`. DLR accepts `assets=`. See the [archive API](../api/hyperproc-archive.md) for backend signatures.

## Select, download, and read

```python
if hits:
    paths = hp.download(hits[:1], "data/emit")
    primary = next(p for p in paths if "_RFL_" in p.name and p.suffix == ".nc")
    ds = hp.open(primary, sensor="EMIT", level="L2A")
    hp.describe(ds)
```

Download writes files, can transfer several GB for a scene, and needs the archive's credentials. Results may include ancillary files required by the reader. Inspect the selected granule and available space first. The [first dataset guide](../getting-started/quickstart.md) continues with a window, QA, indices, and export.

For NASA CMR, configure Earthdata credentials once before an unattended run:

```bash
python -c "import earthaccess; earthaccess.login(persist=True)"
```

The downloader calls `earthaccess.login()`; it can prompt if stored credentials
are unavailable. `hp.archive.can_download("EMIT", "L2A")` is a local credential
preflight, not a provider-authentication check. See [data access](../getting-started/data-access.md).

## NEON deliveries contain flightlines

```python
months = hp.search("NEON", "L1", site="BART", date=("2023-01-01", "2023-12-31"), count=1)
flightlines = hp.files(months)  # authenticated listing using NEON_TOKEN
print(flightlines)
# Download selected reflectance flightlines after inspecting the listing:
# paths = hp.download(flightlines[:1], "data/neon")
```

NEON search results describe site-month deliveries. Date filtering operates at month granularity; `hp.files()` expands a delivery into individual flightlines. For CMR and DLR, `files()` keeps the existing granule records.

## DLR mission access and policy

DLR downloads use the provider's CAS sign-on form. The backend does not use HTTP Basic authentication. EnMAP and DESIS can need distinct accounts or mission approvals. If the first sign-in requires an Acceptable Usage Policy, inspect it with `hp.archive.dlr.read_policy("ENMAP")` and accept it through the provider's browser flow. The downloader also supports `accept_policy=True` for a policy you have reviewed and agreed to.

See [data access](../getting-started/data-access.md) for credential names and search coverage. Unsupported instruments or levels raise an explanatory error; an empty supported search can mean no observations match the query or no processed product was published.

## Draw and select in a notebook

```python
m = hp.search_map(bbox=(-121.0, 34.0, -119.8, 35.1))
m  # display in a notebook cell
```

Choose sensor, level, and dates in the panel, or draw a box. Click footprints to select scenes and inspect available quicklooks. Then use a separate cell:

```python
print(m.selected)
# Run when you are ready to fetch the selected files:
# paths = hp.download(m.selected, "data/selected")
```

A map can display an existing result set with `hp.search_map(results=hits)`. The map is an optional Jupyter widget; the static documentation displays saved output and does not run archive queries. Public quicklooks depend on provider availability; missing imagery does not imply missing science data.

The [search and download notebook](../tutorials/search-download-tutorial.md) retains the detailed examples and saved results for the current collection table.
