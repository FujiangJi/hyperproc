# Atmospheric correction with ISOFIT

hyperproc prepares inputs, orchestrates ISOFIT's `apply_oe`, reads the retrieval, and optionally maps and exports it. The inverse model and its assumptions come from the ISOFIT workflow. See [ISOFIT's description](https://isofit.github.io/isofit/latest/) for the upstream framework.

## Preconditions

- A supported at-sensor input with correct radiometric meaning and calibration.
- Wavelengths and band widths compatible with the selected engine.
- Acquisition time, location, solar/view geometry, and elevation information.
- A working ISOFIT installation with required engines and data assets.
- A bounded initial test window and enough free disk space.

Install `hyperproc[atmos]` and run `hyperproc-atmos-setup --check` first. The
default sRTMnet route also requires compiled 6S, so `gfortran` and `make` are
needed even when no explicit `6s` engine was selected. LibRadTran additionally
needs the C compiler and GSL. Assets default to `~/.isofit`; use `--base` for
a shared asset directory. See [installation](../getting-started/installation.md)
for the exact package constraints and setup commands.

NEON's current DP1 reflectance reader is not a radiance source. PRISMA L2B surface radiance must not be treated as L1 at-sensor radiance. PACE L1B uses its dedicated TOA-reflectance conversion. Reader support alone does not prove that every level/grid combination is suitable for this route.

## One-call processing

```python
from hyperproc.atmos import check, process

report = check(engines=("sRTMnet",))
if not report["ok"]:
    raise RuntimeError("Provision the missing ISOFIT assets before processing")

products = process(
    "/path/to/supported_L1_product",
    "products/ac-window",
    work_dir="work/scene-window-srtmnet",
    stages=("ac",),
    window={"y": (3000, 3500), "x": (400, 900)},
    workers=4,
    layers=("aot550", "h2o"),
    quality=True,
    format="GTiff",
)
```

Replace the scene and window before execution. This call writes prepared inputs, work products, retrieved imagery, and sidecars. Worker count four is a conservative example, not an established optimum.

## Internal stages

1. `prepare_inputs()` writes radiance, location, observation geometry, and spectral metadata in ISOFIT-compatible ENVI files.
2. `build_command()` resolves retrieval parameters and engine controls.
3. `correct()` runs or resumes the retrieval; `read_outputs()` can reopen a completed run.
4. `to_map_grid()` uses an existing map grid, EMIT GLT, or appropriate geolocation pathway.
5. `process()` exports the cube and requested auxiliary products.

The standardized radiance units are µW cm⁻² nm⁻¹ sr⁻¹. The implementation limits radiative-transfer inputs to 350–2500 nm; unsupported bands are removed rather than assigned an invented atmosphere. Preserve the returned band table.

## Engine and retrieval choices

| Option | Meaning / caution |
|---|---|
| `engine="sRTMnet"` | Emulator-backed route; requires model assets |
| `engine="6s"` | 6S LUT engine; aerosol settings exposed |
| `engine="LibRadTran"` | libRadtran LUT engine; separate build/assets required |
| `surface` | Surface prior/model; influences retrieval behavior, including dark surfaces |
| `num_neighbors` | Analytical-line atmospheric interpolation controls |
| `aot_prior_sigma` | Aerosol prior uncertainty setting; not a generic accuracy knob |
| `config_overrides` | Advanced ISOFIT settings; record every override |
| `segmentation_size` | Superpixel configuration, affecting resources and interpolation |

## Small windows and analytical-line neighbors

`resolve_neighbors()` caps requested counts using the valid pixel fraction,
window size, and `segmentation_size`, with a minimum of five. The conservative
estimate is half the nominal segment count. If a previous label image is
available, 80% of its measured segment count can lower the cap, but never
raise it. This avoids a larger neighbor request merely because a completed
work directory now has a label image, while allowing a smaller measured
segmentation to reduce the request after a failure.

The atmospheric runner also checks netCDF configuration files before starting
ISOFIT. Setup can repair missing final newlines; the runner warns rather than
editing those files. See [configuration](../getting-started/configuration.md).

## Optional satellite BRDF stage

`stages=("ac", "brdf")` enables the satellite normalization route. Airborne grouped correction belongs in the separate [airborne workflow](airborne.md), not this stage list.

## Validation and reuse

Compare retrievals over matching ground and wavelengths; use multiple spectral regions and independent information where available. Agreement with a provider's reflectance is informative but is not ground truth. A completed work directory can be reused: a short elapsed time may describe export or interpolation, not a fresh atmospheric retrieval.

See [atmospheric API](../api/hyperproc-atmos.md), [input preparation](../api/hyperproc-atmos-inputs.md), and [configuration](../getting-started/configuration.md).
