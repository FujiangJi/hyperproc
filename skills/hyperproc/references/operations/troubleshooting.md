# Troubleshoot symptoms without universal guesses

| Symptom | First checks | Avoid |
|---|---|---|
| `hp.atmos`/`hp.correct` AttributeError | Explicitly import the requested namespace | Assuming root import exposes every submodule |
| Product cannot be sniffed/opened | Primary file, actual level, expected siblings and implemented reader | Renaming a file to trick detection |
| Wrong cross-level comparison | Grid table, complete affine/GLT/lat-lon, same acquisition and region | Reusing indices just because shape/UTM matches |
| Suspiciously fast/identical retrieval | [Reuse symptoms](work-directory-reuse.md), existing provenance/settings | Declaring a fresh runtime benchmark |
| Repeated ISOFIT worker crash | Actual traceback/assets/resources; netCDF rc final newline; explicit NCRCENV_RC | “Every macOS crash is .dodsrc” |
| Missing engine executable | Engine-specific `--check`, compiler discovery, built 6S/uvspec | Treating unpacked source as a working binary |
| Out of memory | Window/bands/chunks/worker concurrency, phase memory and disk | Repeating a full-scene run or persisting all cubes |
| 403/login/policy error | Backend credentials/mission approval/token expiry/policy status | All 403s mean the same thing; endless retry |
| Download stalls | DLR `.part` progress/announced size versus other backend behavior | Assuming all backends resume identically |
| NDVI near zero or dark plot | Actual units/support/observed surface, finite values and plotting limits | Assuming all near-zero values are water or all dark plots have good data |

Core checks are local `env_report.py`, `sensor_table.py` and a targeted API query. Atmospheric checks are conditional on an atmospheric task; avoid requiring ISOFIT for unrelated spectral debugging.

For `.ncrc`, `.daprc`, `.dodsrc`, the release detects missing final newlines in nonempty files. Setup can append a newline; checks/runner may only warn. Inspect the actual affected file and configuration scope before repair. `NCRCENV_RC` selects an explicit file whose contents are the caller's responsibility. Preserve credentials/configuration and do not rewrite rc files wholesale.

Retain sanitized exception type/phase, versions, source/window/settings and last completed stage. Correct one demonstrated cause before retrying. Do not silently alter units, sensor, masks, engine, priors or force diagnostic gates to make a run finish. Report partial work honestly.
