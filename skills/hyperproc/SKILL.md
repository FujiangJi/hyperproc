---
name: hyperproc
description: Install and diagnose hyperproc environments, find and inspect supported hyperspectral products, and prepare validated surface reflectance and analysis outputs using atmospheric, quality, spatial, spectral, topographic and BRDF workflows. Use for hyperproc processing on Linux, macOS, Windows or WSL2, and scientific interpretation of its outputs.
---

# hyperproc: environment to science-ready reflectance

Use the user's actual interpreter, provider files and research objective. The reviewed baseline is released **hyperproc 0.1.2**; live helpers read installed code. “Science-ready” means suitable for the stated analysis with checked units, support, QA, geometry and provenance—not simply that every available correction ran.

## First actions

1. Locate this skill directory and invoke helpers by absolute path, using the intended Python. `scripts/env_report.py` reports installed metadata; opt into `--credentials` or `--atmos-engine sRTMnet` only when relevant. If installation is needed, select the OS chapter in [installation](references/installation/index.md).
2. Run `scripts/sensor_table.py` for current reader/archive support. Consult the **[sensor grid table](references/sensors/grids.md)** before selecting a window or comparing product levels. Explicitly import processing namespaces: `from hyperproc.atmos import process` and `import hyperproc.correct as hc`; fresh `import hyperproc as hp` alone does not expose `hp.atmos`/`hp.correct`.
3. Inspect metadata first with `scripts/inspect_product.py`; use `--sample --window Y0 Y1 X0 X1` for bounded value checks. Confirm actual quantity, units, spectral support, companions, acquisition identity, QA availability and ground region.
4. Before **scene/asset downloads**, report selected files, known volume plus unknown-size items, destination/free disk and unpack/work allowance. Prepare a concrete plan with `scripts/download_plan.py`; obtain approval unless this exact selection and budget are already explicitly authorized. Unknown sizes are not zero. A broad “process data” request does not authorize an unbounded multi-GB transfer.
5. Choose a route below; verify each intended installed call with `scripts/api_index.py --symbol QUALIFIED_NAME --runtime --doc`. AST source mode is available without optional imports. The [offline API atlas](references/api/index.md) covers every baseline module/function/class/member in small separate files.

## Choose and finish the appropriate route

| Input / goal | Read first | Result |
|---|---|---|
| Existing surface reflectance | [Provider route](references/workflows/reflectance-route.md), [QA/spectral](references/workflows/quality-spectral.md) | Validated, masked reflectance; requested features/export |
| Supported at-sensor input | [Atmospheric route](references/workflows/atmospheric-route.md), [assets](references/installation/atmos-assets.md) | Retrieved surface reflectance, mapping, QA and requested retrieval layers |
| Airborne reflectance group | [Airborne route](references/workflows/airborne-route.md), [correction detail](references/workflows/advanced-corrections.md) | Evidence-gated topo/FlexBRDF, checked overlaps and spectra |
| Satellite surface reflectance | [Satellite route](references/workflows/satellite-route.md) | Deliberately chosen MCD43-based target geometry, factors and QA |
| Cross-sensor analysis | [Spectral support](references/workflows/quality-spectral.md), [spatial/export](references/workflows/spatial-export.md) | Matched support and verified ground correspondence |
| Find/download scenes | [Acquisition](references/operations/acquisition.md), [archive detail](references/operations/archive-operations.md) | Approved selected provider delivery with required companions |

Load only the selected route and needed API symbols. Installation, one index, debugging, and a full correction campaign require different amounts of context. Do not load all references or all machine inventories by default.

## Critical decisions

- EMIT atmospheric windows use the sensor grid; default reader GLT mapping is different. PRISMA L1 swath and L2D UTM indices differ. EnMAP L1B VNIR/SWIR are separate. Check the table and actual transform/geolocation, even for nominally mapped level pairs.
- NEON `L1` is surface reflectance, PRISMA `L2B` is surface radiance, and PACE `L1B` is TOA reflectance. Level names or variable names alone do not identify valid atmospheric inputs.
- Dataset angles are degrees; low-level kernels generally use radians. Wavelength/FWHM convention is nm. Missing cloud information is unknown sky status; QA build does not automatically mask values.
- Keep topo `skip`/`refuse`/`inconclusive` and angular-diversity failures meaningful. Apply a BRDF model to the same prior correction state used to fit it. MCD43-filled/neutral factors are not successful physical normalization.
- Use unique scene/window/settings work directories. **Identical medians, repeated stored runtimes or suspiciously fast retrievals on different regions can indicate reused work painted onto the wrong ground.** Read [reuse symptoms](references/operations/work-directory-reuse.md); `scripts/run_context.py` helps distinguish run identities.
- Do not invent CRS, unresolved bands, cloud flags or uncertainty propagation. Smoothing and gap filling are optional modeling choices, not steps required to make reflectance scientifically valid.

## Completion and maintenance

Follow the **[science-readiness acceptance criteria](references/workflows/science-ready.md)** and [execution/provenance](references/operations/execution-validation.md). Deliver requested products, generating script, band/QA/geometry/coefficient records as relevant, actual disk checks, and limitations. Report partial/failed/unsupported stages honestly.

Live scripts follow installed signatures/tables, but scientific advice does not automatically become validated for a new release. Use [version maintenance](references/operations/version-maintenance.md) when behavior differs. [Validation evidence](references/provenance/validation.md) distinguishes source coverage, synthetic checks and real scientific validation.
