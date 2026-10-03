# Troubleshooting

## Import fails

Confirm Python {{ python_requires }}, the active environment, and `hp.__file__`. Install this checkout with `pip install -e .` from the repository root. Resolve the actual missing dependency from the traceback; a different installed package with the same name may not be this checkout.

## “Cannot tell what this product is”

Check provider filenames, sensor/level, and file extensions. Explicit identification can resolve a renamed supported delivery, but cannot turn an unsupported export into a provider product. `hp.open()` is not a generic GeoTIFF reader.

## Archive search or download fails

Install the `search` extra (or `search-map` for widgets). Check `hp.archive.describe()` for searchable levels and `hp.archive.credentials()` for locally configured credentials. Search is anonymous; NEON flightline listing and all archive downloads need credentials. A configured DLR account can still lack mission access or require policy acceptance. See [search and download](../workflows/search.md).

For Earthdata, run `python -c "import earthaccess; earthaccess.login(persist=True)"`
once before an unattended job. The CMR backend calls `earthaccess.login()`,
which may prompt when credentials are missing.

## Optional dependency or atmospheric engine missing

Use the capability extra named by the error: `hyperproc[brdf]` for Earth
Engine, `hyperproc[srf]` for published response spreadsheets, or
`hyperproc[atmos]` for ISOFIT. Compiled engines also need system/environment
build tools, which pip does not supply. Run `hyperproc-atmos-setup --check`
or `--check --engine LibRadTran` to see missing tools/assets without downloads.
See [installation](../getting-started/installation.md).

## ISOFIT workers crash or report a netCDF configuration warning

Check the `.ncrc`, `.daprc`, and `.dodsrc` paths named by the warning. A
nonempty file without a final newline is flagged by the current package's
netCDF diagnostic. `hyperproc-atmos-setup --check` reports affected
home-directory files; running setup appends the missing newline there.
For a specific affected file, append only the final newline, for example:

```bash
printf '\n' >> "$HOME/.dodsrc"
```

Use the actual path from the warning. Work-directory files need the same
repair if reported. Alternatively, set `NCRCENV_RC` to a newline-terminated
copy; when that variable is present, the atmospheric runner skips its default
home/work scan. This addresses the reported configuration issue, not every
possible retrieval or worker failure.

## DLR download leaves a .part file

A `.part` file retains bytes from an unfinished transfer. Rerun the same
selected download to resume when the server supports Range. No-progress
failures eventually stop; the file is retained for a later call. Check the
reported exception and account access rather than renaming the partial file
as a finished product. See [DLR recovery](../workflows/search.md#interrupted-dlr-downloads).

## Atmospheric extra does not install on Python 3.13

Use a Python 3.12 environment. The ISOFIT 4.1.5 installation used for this
release requires Python `>=3.11,<3.13`, while hyperproc's core requirement
remains {{ python_requires }}. See [installation](../getting-started/installation.md).

## Missing CRS on export

Determine whether the input is a geolocated swath, a raw detector grid, or a product missing metadata. Use the correct GLT/georeferencing path where available. Do not assign a CRS solely to silence the writer.

## BRDF fit rejected

Inspect robust angular span, kernel conditioning, masks, and the sampling region. A cropped swath may discard the useful view-angle range. Do not routinely bypass the gate with `force=True`.

## Topographic verdict is not `correct`

Read per-band status, residual effects, terrain variability, and block agreement. Provider corrections or vegetation/terrain confounding can affect the fit. A refusal is not necessarily a software malfunction.

## A saved retrieval ignores my new settings

The work directory may contain a completed run. Inspect logs and provenance. Use an intentionally separate experiment directory or the documented redo/overwrite controls; do not delete unknown folders to force progress.

## Band unavailable or resampling returns NaN

Check wavelength range, bad-band policy, target response coverage, and sharpening safeguards. Missing SWIR observations cannot be recovered by changing an index name or interpolating a narrow output grid.

## “Clear 100%” seems implausible

Inspect which provider masks actually exist and which derived flags were requested. Absence of a flag is not proof that the corresponding condition is absent.

## Large memory usage or slow export

Avoid full-cube `.values`, reduce the analysis region, inspect source chunking, and bound concurrency. Compare first-run and cached-run timings separately. See [performance](../workflows/performance.md).

## Logo stays light in dark mode

Use the provided theme-aware classes/template rather than inserting the light SVG alone. Both dark SVG files must be present. A hard refresh clears an old stylesheet; the website's toggle, not only the operating-system theme, controls the current Material color scheme.
