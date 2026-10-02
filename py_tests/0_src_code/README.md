# py_tests — one pipeline, six instruments

Each script takes one scene from an instrument and carries it the whole way:
find or copy the data, read it, export it in two formats, correct it along two
routes, and compare the results.

```
L1 radiance  ──atmospheric──▶  reflectance  ──BRDF──▶  normalised
L2 reflectance          (the provider's own AC)  ──BRDF──▶  normalised
```

Running both routes is the point. The provider already published a corrected
L2; doing our own correction of the same radiance and comparing the two is
what tells you whether `hyperproc.atmos` is working.

## Running one

```bash
conda activate gcrl
cd py_tests/0_src_code

python emit_pipeline.py
python enmap_pipeline.py
python desis_pipeline.py
python pace_pipeline.py
python prisma_pipeline.py
python tanager_pipeline.py
```

**Yes — you run the per-sensor script, and it uses `pipeline.py` by itself.**
Each one is about thirty lines: a `SensorConfig` and a call.

```python
from pipeline import SensorConfig, run

CONFIG = SensorConfig(
    name="DESIS",
    l1_glob="DESIS/DESIS-HSI-L1C-*-SPECTRAL_IMAGE.tif",
    l2_glob="DESIS/DESIS-HSI-L2A-*-SPECTRAL_IMAGE.tif",
    window={"y": (600, 800), "x": (600, 800)},
    subset="isel",
    source="copy",
)

if __name__ == "__main__":
    raise SystemExit(run(CONFIG))
```

Python puts a script's own directory at the front of `sys.path`, so
`from pipeline import ...` finds the file next to it. You can run it from
anywhere:

```bash
python /data/fujiang/Hyperspectral_data_processing/py_tests/0_src_code/desis_pipeline.py
```

`pipeline.py` is not meant to be run on its own — it has no `main`.

## Two EMIT scripts

`emit_pipeline.py` is 40 lines and uses the shared engine. `emit_pipeline_standalone.py`
is the same pipeline written out in full, 881 lines, importing nothing but
`hyperproc`. Both work and both produce the same products.

The standalone is there to read and to lift: everything a run does is visible
in one file, in order. The engine version is there so that a fix lands in six
places at once. Pick whichever fits what you are doing.

## Why one engine and six configs

The alternative was six copies of an 800-line script. Four real bugs turned up
while getting these to work, and each would have had to be found and fixed six
times:

| Bug | Symptom |
|---|---|
| `flag_masks` is a space-separated string, not a list | `int(' ')` crashed the quality step |
| Colour limits hard-coded to 0–0.5 | a dark scene rendered as a black rectangle |
| **ISOFIT's working directory did not depend on the window** | **the second run silently reused the first window's retrieval** |
| A swath has no CRS, and a raster file needs one | export and the BRDF product both failed on PACE and PRISMA |

The third is the one worth remembering. `process()` deliberately reuses a
retrieval it finds in `work_dir` — that is what makes the AC+BRDF run take
seconds instead of minutes. Share one folder between two windows and it reuses
the *wrong* retrieval: identical numbers, identical reported runtime, painted
onto different ground. The only visible symptom was one panel looking too
dark. `work_dir_for()` now names the folder after the window.

## Going in stages

A full run is minutes of retrieval. Look before you leap:

```bash
python enmap_pipeline.py --stage read     # read, export, two figures
python enmap_pipeline.py --stage ac       # + the atmospheric correction
python enmap_pipeline.py                  # + BRDF, quality, all seven figures
```

`--stage read` prints what the window actually contains:

```
window content: NDVI +0.579, 865 nm 0.205, 95 % vegetated, 100 % valid
```

and says so when it does not:

```
window content: NDVI +0.028, 865 nm 0.025, 0 % vegetated, 100 % valid
  ^ that reads as open water. The BRDF step borrows MODIS *land*
    kernels, so its output here will look like a result and mean little.
```

That check exists because the first EMIT run was over ocean, and two rounds of
processing were spent before anyone noticed. Move the window with
`--window Y0 Y1 X0 X1`.

## What each sensor needs to know about itself

| | L1 used | window indexes | data from | note |
|---|---|---|---|---|
| EMIT | L1B | the **detector** grid | CMR | L2A is orthorectified, so the window is carried across by ground coordinates |
| EnMAP | **L1C** | the shared UTM grid | DLR | not L1B: its two detectors are not co-registered until L1C |
| DESIS | L1C | the shared UTM grid | **copy only** | DLR publishes only L2A; L1B/L1C are Teledyne's |
| PACE | L1B | the shared swath | CMR | the L1B is TOA **reflectance**, not radiance |
| PRISMA | L1 | the **swath** | copy only | L2D is UTM, so the window is reprojected across |
| Tanager | radiance | the shared UTM grid | copy only | Planet sells it; no public search API |

`subset=` in each config says which of those three cases applies: `"isel"` when
both levels share a grid, `"detector"` for EMIT, `"reproject"` for PRISMA.

## Where the data comes from

`--source auto` (the default) downloads where the archive allows it and copies
from `tests/data` otherwise, saying which it did. The download matches the two
levels **by name**, because the comparison at the end only means anything if
the L1 and the L2 are the same overpass.

```bash
python pace_pipeline.py --source copy       # never touch the network
python pace_pipeline.py --source download   # insist on the archive
```

Downloading needs credentials, which differ by archive and none of which are
needed to search:

| Archive | For | Needs |
|---|---|---|
| NASA CMR | EMIT, PACE | `~/.netrc` or `EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` |
| DLR | EnMAP | an EnMAP Access Service account |
| — | DESIS, PRISMA, Tanager | nothing: they are copied from `tests/data` |

The BRDF step additionally needs Earth Engine (`earthengine authenticate`) to
fetch MODIS MCD43A1 kernel weights. Without it the run continues and says what
is missing rather than failing.

## What comes out

```
py_tests/
  1_data/<SENSOR>/            the granule pair
  2_outputs/<SENSOR>/
    01_read/                  both levels, GeoTIFF and ENVI, plus band tables
    02_ac/                    our reflectance, with aot550, h2o and quality
      isofit_win<Y0-Y1_X0-X1>/  one retrieval per window — see above
    03_ac_brdf/               that reflectance, BRDF-normalised
    04_l2_brdf/               the provider's L2, BRDF-normalised
    figures/                  seven PNGs
    summary.json              every number the run measured
```

| Figure | Shows |
|---|---|
| `01_inputs.png` | the two levels this run starts from |
| `02_geometry.png` | sun and view angles — without these there is no BRDF step |
| `03_ac_vs_provider.png` | **ours against the provider's**, as maps, a difference and a scatter |
| `04_spectra.png` | all four products on one axis, and what each step changed |
| `05_brdf_l2.png` | the provider's L2 before and after BRDF |
| `06_brdf_ac.png` | our reflectance before and after BRDF |
| `07_quality.png` | the bit layer and what each flag covers |

## Reading the results

From the runs on 2026-10-02, at 865 nm:

| Sensor | pixels | median difference | RMSE | r |
|---|---|---|---|---|
| EMIT | 20,325 | +0.0039 | 0.0040 | 1.0000 |
| Tanager | 40,000 | −0.0027 | 0.0037 | 0.9996 |
| PACE | 42,541 | −0.0040 | 0.0143 | 0.9937 |
| EnMAP | 40,000 | +0.0029 | 0.0200 | 0.9823 |
| DESIS | 27,673 | −0.0021 | 0.0175 | 0.9140 |
| PRISMA | 42,697 | −0.0010 | 0.0580 | 0.6747 |

PRISMA is the outlier and also the only sensor whose two levels are on
different grids, so part of that scatter is resampling rather than retrieval.
The difference map in `03_ac_vs_provider.png` distinguishes them: geometric
texture means registration, a smooth gradient means aerosol.

**The BRDF angular tests will say they cannot tell**, on every sensor:

```
model agreement not testable: only 1 azimuth bins have 200+ pixels;
this scene does not span enough azimuth to test the shape
```

A 200 × 200 window spans under a degree of view zenith and almost no azimuth,
so there is no angular signal to measure. That is a fact about the window, not
a failure of the correction — testing the kernel model properly needs a whole
scene. The script reports it rather than inventing a number.

## Adding a sensor

Write a config. If its two levels share a grid, that is the whole job:

```python
CONFIG = SensorConfig(
    name="NEWSAT",
    l1_glob="NEWSAT/*_radiance.nc",
    l2_glob="NEWSAT/*_reflectance.nc",
    window={"y": (0, 200), "x": (0, 200)},
)
```

If they do not, `subset=` needs a case in `subset_l2()` — and it is worth
being explicit about why, because getting it wrong compares two different
pieces of ground and nothing crashes.
