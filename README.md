# hyperproc

[![Docs](https://img.shields.io/badge/docs-fujiangji.github.io-informational)](https://fujiangji.github.io/hyperproc/)
[![PyPI](https://img.shields.io/pypi/v/hyperproc)](https://pypi.org/project/hyperproc/)
[![Python](https://img.shields.io/pypi/pyversions/hyperproc)](https://pypi.org/project/hyperproc/)
[![License](https://img.shields.io/pypi/l/hyperproc)](https://github.com/FujiangJi/hyperproc/blob/main/LICENSE)
[![Status](https://img.shields.io/pypi/status/hyperproc)](https://pypi.org/project/hyperproc/)


<!-- Two more badges belong here once they are true. Adding them early shows
     "not found", which looks broken rather than early:

[![conda-forge](https://img.shields.io/conda/vn/conda-forge/hyperproc)](https://anaconda.org/conda-forge/hyperproc)
[![Downloads](https://static.pepy.tech/badge/hyperproc)](https://pepy.tech/project/hyperproc)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](coming soon)
-->

Readers, topographic and BRDF correction, and atmospheric
correction for airborne and satellite imaging spectrometers.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FujiangJi/hyperproc/main/docs-site/docs/assets/logos/rectangular-dark.svg">
  <img src="https://raw.githubusercontent.com/FujiangJi/hyperproc/main/docs-site/docs/assets/logos/rectangular.svg" alt="hyperproc" width="720">
</picture>

**Documentation: <https://fujiangji.github.io/hyperproc/>**

* **Readers** (`hyperproc.open`) return one xarray contract for AVIRIS-3/5/NG/Classic,
  NEON AOP, EMIT, PACE OCI, DESIS, EnMAP, PRISMA and Tanager: a lazy
  `reflectance`/`radiance (y, x, wavelength)` cube with `wavelength`, `fwhm`,
  `good_wavelength`, `band_index`, a CRS and GDAL transform, and the geometry
  layers `sza, saa, vza, vaa, slope, aspect, cos_i, raa, elev` where the product
  carries them.
* **Finding granules** (`hyperproc.search`, `hyperproc.download`): start from a
  place and a date rather than from a file you already have. Three archives
  answer, chosen by the `(sensor, level)` pair you ask for - NASA's CMR for
  EMIT, PACE and AVIRIS-3/-5; NEON's Data API for AOP flightlines; DLR's EOC
  STAC catalogue for EnMAP and DESIS - and all three return the same granule
  record, so the rest of a workflow does not care which one answered.
  **Searching every archive is anonymous**; only the bytes are gated, and each
  backend raises with its own registration address rather than failing
  quietly. `hyperproc.archive.credentials()` says which archives this process
  could download from without printing a secret, and `can_download(sensor,
  level)` answers that for one collection before anything is requested.
  NEON publishes a site-month at a time rather than a granule, so
  `hyperproc.files` opens one up into the flightlines inside. Granules carry a
  `browse` quicklook where the archive publishes one anonymously - EMIT and
  AVIRIS do, DLR's sit behind its sign-on, and CMR lists one for every PACE
  granule that was never written. PRISMA, Tanager and the AVIRIS-NG and
  Classic archives cannot be searched from here at all, and say where they
  live instead of returning an empty list, as do the levels a reader opens but
  no archive here publishes (DESIS L1B/L1C, NEON L3);
  `hyperproc.archive.describe()` prints all three cases.
  `hyperproc.search_map()` is the same search on a map: draw the box, click
  footprints to select them and to see their quicklooks, then
  `hyperproc.download(m.selected, "data/")`. Walked end to end over all
  thirteen collections in `tests/0_src_code/search_download_tutorial.ipynb`.
* **Correction** (`hyperproc.correct`): SCS+C topographic correction with a measured
  verdict, FlexBRDF for airborne flightline groups, seam checks between adjacent lines.
* **Satellite BRDF** (`hyperproc.correct.nbar`): one overpass cannot measure its own
  angular response, so the c-factor method (Roy et al. 2016) borrows the shape from
  MODIS MCD43A1, fetched for the scene's footprint and date and cached. Normalises to
  a fixed Sun and nadir view, or to the observed Sun with the view effect removed.
  Also available as `hyperproc.atmos.process(..., stages=("ac", "brdf"))`; see
  `tests/0_src_code/emit_tutorial.ipynb`.
* **Quality** (`hyperproc.quality_flags`): every provider's masks folded into one
  `uint16` bit layer with CF `flag_masks`/`flag_meanings`, so `cloud`,
  `dilated_cloud`, `cloud_land`, `cldice` and the rest stop being nine different
  questions. `quality_apply` masks a cube; `process` writes `<stem>_quality.tif`
  beside every product with the bit table in its GeoTIFF tags.
* **Spectral transforms** (`hyperproc.spectral`): a cube in, a cube out.
  `smoothing`, `continuum` (convex-hull removal), `derivatives` (Savitzky-Golay),
  and `bands` for addressing a band by wavelength rather than by number. Each
  works inside runs of usable bands, so no filter or hull spans a water-vapour gap.
* **Spectral resampling** (`hyperproc.resample`): one matrix, so a whole EMIT
  scene becomes Landsat 8 bands in 7 seconds. Name the target by resolution
  (`step=10, fwhm=15`), by explicit bands, by `like=another_dataset`, or by
  `sensor="SENTINEL2A"`, which downloads and caches the agency's own measured
  response (`hyperproc.spectral.srf`: Sentinel-2 from ESA, Landsat 4/5/7/8/9
  from USGS, PlanetScope 4/8 from published band edges). Reports the fraction
  of each target band the source actually measured and returns NaN instead of
  renormalising, and refuses to invent resolution the source does not have.
* **Spectral features** (`hyperproc.features`): a cube in, a map out.
  `spectral_index` takes a named index or a formula written over wavelengths
  (`"(R800 - R670) / (R800 + R670)"`, parsed as a whitelisted expression), plus
  `band_depth`. Addressed by wavelength, so one call runs unchanged on EMIT at
  285 bands, PACE at 122 and AVIRIS at 425.
* **Coregistration** (`hyperproc.coregister`): two products of the same ground rarely
  land on the same pixel, and cropping to a common extent aligns the corners while
  leaving the content offset. Phase correlation on one band measures the shift to
  about a tenth of a pixel, insensitive to brightness differences between sensors,
  and checks itself by matching tiles independently. Corrects by moving the
  georeferencing (exact, free) or by resampling onto the reference grid.
* **Export** (`hyperproc.to_geotiff`, `hyperproc.to_envi`): streamed, band-interleaved
  GeoTIFFs with wavelength band names, provenance JSON and internal overviews; or ENVI
  flat binaries whose `.hdr` states `wavelength`, `fwhm` and `bbl` as numbers, so band
  centres, widths and the bad-band list survive export. `to_raster(..., format=)` picks
  one, and `process(format="ENVI")` writes whole products that way. ENVI has no
  compression, so a full EMIT product is about 5.1 GB against 2.2 GB deflated.
* **R-compatible smoothing** (`hyperproc.spline_gapfill`): the published PRISMA route,
  despike with a port of `pracma::findpeaks`, mask the artefact ranges, fit a smoothing
  spline and gap-fill, then mask the water bands. The spline is a port of R's
  `stats::smooth.spline`, verified against R on real spectra to 1.5e-8 with an identical
  NaN pattern, and the despike step is bit-identical. Flags which reported bands are
  spline fill rather than measurement.
* **Cosmetic smoothing** (`hyperproc.smooth_spectra`, optional): removes the
  band-to-band structure a per-pixel retrieval leaves, the way some providers do
  before publishing. Never applied automatically, and recorded in the attributes.
* **Atmospheric correction** (`hyperproc.atmos`, optional): drives ISOFIT's
  `apply_oe` from any L1B radiance dataset with the sRTMnet emulator (JPL's route),
  6S or libRadtran filling the look-up table (`engine=`, with `aerosol_model=` on
  the last two). The retrieval's own knobs are exposed where they matter:
  `num_neighbors=` (how far the atmospheric state is interpolated, per term),
  `aot_prior_sigma=` (ISOFIT's tight aerosol prior is why retrieved AOT sits below
  the providers'), `surface=` (the spectral prior, which decides dark-water pixels),
  and `config_overrides=` for anything else in the ISOFIT configuration.
  `correct(redo="line")` reworks only the interpolation, keeping the look-up tables. `hyperproc.atmos.process("EMIT_L1B_RAD_....nc", "products/")` runs the
  retrieval on the sensor grid, orthorectifies through the granule's GLT and writes
  `<stem>_ac.tif` with the retrieved AOT and water vapour beside it; the pieces
  (`prepare_inputs`, `build_command`, `correct`, `read_outputs`) are exposed for
  step-by-step use, see `tests/0_src_code/emit_tutorial.ipynb`.

## Install

```bash
pip install hyperproc                 # readers, correction, export
pip install 'hyperproc[search]'       # + archive search and download
pip install 'hyperproc[search-map]'   # + the interactive map (ipyleaflet)
pip install 'hyperproc[brdf]'         # + Earth Engine, for the satellite BRDF route
pip install 'hyperproc[atmos]'        # + ISOFIT (pins h5py<=3.14, netCDF4<1.7.4; pulls torch and ray)
hyperproc-atmos-setup --base /data/isofit_assets   # once per machine: engines + data assets (~6 GB)
hyperproc-atmos-setup --engine LibRadTran          # optional: fetch and compile libRadtran (needs gcc, gfortran, make, gsl)
hyperproc-atmos-setup --check         # what is in place
```

**Platforms.** The core - readers, topographic and BRDF correction, spectral
transforms, quality, resampling, export - runs on Linux, macOS and Windows.
`[atmos]` is Linux and macOS only: ISOFIT pulls ray and torch, and the
radiative-transfer engines need a Fortran compiler (6S) and a C toolchain with
GSL (LibRadTran), neither of which builds on Windows.

Searching an archive needs no account. Downloading needs the archive's own,
and all of them are free:

| Archive | Register at | hyperproc reads |
|---|---|---|
| NASA | <https://urs.earthdata.nasa.gov> | `~/.netrc`, or `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` |
| NEON | <https://data.neonscience.org/myaccount> | `NEON_TOKEN` - **required since June 2026**; the data endpoint returns a bare 403 without one |
| DLR, EnMAP | <https://www.enmap.org/data_access/> | `ENMAP_USERNAME`/`ENMAP_PASSWORD` |
| DLR, DESIS | <https://sso.eoc.dlr.de/geoservice/selfservice/register> or EOWEB | `DESIS_USERNAME`/`DESIS_PASSWORD` |

**DLR is two doors.** Both missions' files sit on one server behind one sign-on,
but access is granted per mission, so an account that opens EnMAP need not open
DESIS; `DLR_EOC_USERNAME`/`DLR_EOC_PASSWORD` is a shared fallback for whichever
has no pair of its own. That server takes **no HTTP Basic auth** - it answers
403 to an `Authorization` header and redirects everything else to its CAS
single sign-on - so `download` carries the login form through once per mission
and keeps the session. The first sign-in may stop at an Acceptable Usage
Policy; agreeing to it is yours to do, so hyperproc prints what it says rather
than clicking it. Read it with `hyperproc.archive.dlr.read_policy("ENMAP")`,
then accept it in a browser once or pass `accept_policy=True`.

The satellite BRDF route needs Earth Engine credentials once:
`earthengine authenticate`. The airborne route fits its own kernel model from
the flight's own angles and needs nothing.

The atmospheric-correction assets (compiled 6S, sRTMnet weights, spectral
libraries) cannot ship in a wheel; `hyperproc-atmos-setup` fetches them with
ISOFIT's own downloader into one shared base directory recorded in
`~/.isofit/isofit.ini`. Building 6S needs `gfortran` and `make`.

## Tests

```bash
pip install 'hyperproc[test]'
pytest                      # 711 tests, ~7 minutes
pytest -m "not data"        # the 493 that need no granules
pytest -m network           # 6 more that check the archives still behave as recorded
```

Most tests have an answer known in advance rather than a recorded snapshot: a
straight line has a flat derivative, resampling onto the grid you are already on
returns the input, a planted pixel offset comes back out of the coregistration.
Four groups are worth naming:

* **readers** - 216 cases over 24 sensor-level combinations, each checked against
  a recorded fingerprint (sizes, wavelengths, geometry, transform) and against
  physics that must hold whatever the reader does;
* **the R port** - `hyperproc.spline_gapfill` reproduces a published R pipeline,
  and is checked against R's own output on 40 real PRISMA spectra, checked in.
  Regenerate with `python tests/tools/make_r_reference.py` (needs R with
  `pracma` and `FieldSpectroscopyCC`);
* **atmos** - the parts that can be checked without a retrieval: the sensor
  table, the MODTRAN atmosphere choice, DEM tile naming, config rewriting;
* **archive** - 212 tests. Every search replays a recorded response from CMR,
  NEON and DLR, so the whole of `hyperproc.search` runs offline. Re-record with
  `python tests/tools/make_archive_fixtures.py`, and read the diff. The six
  `network` tests ask whether the recordings are still true, and two of them
  pin assumptions that would otherwise fail silently: that DLR's file server
  still refuses Basic auth, and that its sign-on is still a form this version
  can fill in.

Tests marked `data` open the granules in `tests/data/`, which are not in the
repository. Everything else runs from a clean clone.

## Tutorials

`tests/0_src_code/` holds one executed notebook per instrument, each documenting
every parameter of every call it makes: `emit`, `enmap`, `desis`, `pace`,
`prisma`, `tanager` (whole-scene and windowed), and `aviris3`, `aviris5`,
`avirisng`, `avirisclassic`, `neon` (windowed, since a flightline is too large
to correct whole).

## Citing

See `CITATION.cff`, or the "Cite this repository" button on GitHub.

## License

MIT - see `LICENSE`.
