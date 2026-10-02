---
title: hyperproc documentation
---

<div class="eyebrow">Imaging spectroscopy · Python · {{ source_version }}</div>

# One interface. Many spectral worlds.

![hyperproc — hyperspectral tools for terrestrial ecosystem monitoring](assets/logos/rectangular.svg){ .brand-banner .theme-light }
![hyperproc — hyperspectral tools for terrestrial ecosystem monitoring](assets/logos/rectangular-dark.svg){ .brand-banner .theme-dark }

**Find, read, inspect, correct, and prepare airborne and satellite hyperspectral data through a shared Python interface.** hyperproc brings sensor-specific products into `xarray`, with processing tools for terrestrial ecosystem research and other imaging-spectroscopy applications.

**Installation · Python {{ python_requires }}**

```bash
pip install hyperproc
pip install 'hyperproc[search]'
pip install 'hyperproc[search-map]'
pip install 'hyperproc[brdf]'
pip install 'hyperproc[atmos]'
```

| Extra | Adds |
|---|---|
| *(none)* | readers, correction, export |
| `search` | archive search and download |
| `search-map` | interactive notebook maps (ipyleaflet) |
| `brdf` | Earth Engine for satellite BRDF |
| `atmos` | ISOFIT atmospheric correction |

`[atmos]` also needs its engines and data assets, once per machine:

```bash
hyperproc-atmos-setup
hyperproc-atmos-setup --engine LibRadTran
hyperproc-atmos-setup --check
```

The first line installs the engines and data assets (~6 GB) under `~/.isofit`,
`--engine LibRadTran` is optional, and `--check` inspects what is already
installed. On a shared machine, add `--base /data/shared/isofit_assets` so
every user reads one copy.

[Installation guide: environments, optional features, and setup requirements](getting-started/installation.md)

```python
import hyperproc as hp

ds = hp.open("/path/to/a/supported/provider_product")
hp.describe(ds)
ndvi = hp.spectral_index(ds, "NDVI")  # use suitable reflectance, not radiance
```

<div class="grid cards" markdown>

- **Start with one scene**

    Open a supported provider product, inspect its physical meaning, and make a small first output.

    [Read the quickstart](getting-started/quickstart.md)

- **Find data by place and date**

    Search NASA, NEON, and DLR, select granules in a notebook map, and download provider files.

    [Search and download](workflows/search.md)

- **Find your sensor**

    Product levels, required files, geometry, QA, and reader-specific caveats for airborne and satellite instruments.

    [Explore the sensor guides](sensors/index.md)

- **Follow a worked example**

    {{ notebooks }} original notebooks with {{ saved_figures }} saved figures, plus a curated AVIRIS-3 walkthrough.

    [Browse tutorials](tutorials/index.md)

- **Choose a scientific workflow**

    Atmospheric retrieval, terrain diagnostics, angular normalization, spectral processing, and aligned exports.

    [Use the decision guide](background/decision-guide.md)

- **Look up an API**

    Signatures, defaults, docstrings, and source across {{ api_modules }} Python modules. Private helpers are explicitly distinguished.

    [Open the API reference](api/index.md)

</div>

## Choose the right processing path

| Your input | Next step | Important distinction |
|---|---|---|
| Provider surface reflectance | Inspect QA; choose optional corrections or spectral analysis | Do not repeat atmospheric correction automatically |
| Supported L1 radiance | Optional ISOFIT retrieval | Input units, geometry, and external assets matter |
| Airborne reflectance group | Per-line topographic diagnostics and grouped FlexBRDF | Let diagnostic gates decide whether correction is justified |
| Satellite reflectance | Optional MCD43-based BRDF normalization | Broadband-derived angular shape is not a measured hyperspectral BRDF |

!!! note "Current package documentation"
    Built from the adjacent source and package metadata. hyperproc is MIT licensed; citation and maintainer details are available in the [project guide](project/governance.md). Saved notebook outputs are historical results. See [documentation status](project/status.md) for the snapshot and evidence limits.
