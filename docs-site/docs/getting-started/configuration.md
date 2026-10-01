# Configuration and external assets

There is no single global hyperproc configuration file in this snapshot. Reader and processing functions take explicit keyword arguments; some external systems maintain their own configuration and caches.

## Paths and cache ownership

```python
import os
os.environ["HYPERPROC_CACHE_DIR"] = "/path/to/hyperproc-cache"
```

Set cache configuration before invoking downloads. The default common cache is under the user's home cache directory. MCD43 retrieval also accepts `cache_dir=`/output-directory controls. Keep cache provenance when comparing results across machines or dates.

| Resource | Purpose | Important boundary |
|---|---|---|
| ISOFIT asset base | Radiative-transfer engines, emulator, surface libraries | Managed through ISOFIT setup/configuration |
| ISOFIT work directory | Prepared inputs, LUTs, retrievals, run records | Reused results can bypass a new retrieval |
| MCD43 cache | Parameters and quality for a footprint/date | Requires suitable temporal/spatial coverage |
| SRF cache | Agency response files and parsed arrays | Agency-measured and nominal responses are distinct |
| DEM cache | Elevation inputs when required | Fallback behavior must be checked for your region |

## Work-directory hygiene

Use separate work directories for different scenes, windows, engines, and experiments. Do not rely on a file's shape or a shared directory name to establish that it belongs to the current run. Inspect existing-run messages and provenance before accepting a result.

`overwrite=True` and `redo="all"` can replace retrieval work products. `redo="line"` reruns a narrower interpolation stage while retaining upstream work. A `dry_run` of atmospheric correction can still prepare input files; it is **not a read-only diagnostic**.

## Resources and parallelism

Tutorial worker counts are examples, not hardware-independent defaults. Bound Dask threads, ISOFIT workers, and export block sizes to your machine's available memory and disk throughput. Importing the package sets `GDAL_CACHEMAX` to a default if that environment variable is not already set.

## Credentials

Archive downloads read Earthdata, NEON, and mission-specific DLR credentials from the sources described in [data access](data-access.md). `hp.archive.credentials()` reports availability without printing secrets.

Earth Engine authentication and project authorization are external to the package's scientific algorithms. The local docs do not authenticate accounts. Never commit tokens into tutorials or environment examples.
