---
title: hyperproc documentation
hide:
  - navigation
  - toc
---

<div class="homepage-brand">
  <img class="theme-light" src="assets/logos/wordmark.svg" alt="hyperproc" width="1840" height="410">
  <img class="theme-dark" src="assets/logos/wordmark-dark.svg" alt="hyperproc" width="1840" height="410">
  <div>
    <p class="homepage-brand__eyebrow">AIRBORNE + SATELLITE</p>
    <p>Hyperspectral tools for terrestrial ecosystem monitoring</p>
  </div>
</div>

<div class="eyebrow">Imaging spectroscopy · Python · {{ source_version }}</div>

## One interface. Many spectral worlds.

**Find, read, inspect, correct, and prepare airborne and satellite hyperspectral data through a shared Python interface.** hyperproc brings sensor-specific products into `xarray`, with processing tools for terrestrial ecosystem research and other imaging-spectroscopy applications.

**No conda yet?**

Not sure which you have? `uname -m` prints `arm64` on Apple silicon and
`x86_64` on an Intel Mac; on Linux it prints `x86_64` or `aarch64`. Pick the
box, copy all four lines, run them.

**Mac, Apple silicon**

```bash
curl -fsSLO https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash Miniconda3-latest-MacOSX-arm64.sh
source ~/.zshrc
conda --version
```

**Mac, Intel**

```bash
curl -fsSLO https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
bash Miniconda3-latest-MacOSX-x86_64.sh
source ~/.zshrc
conda --version
```

**Linux, Intel/AMD (x86-64)**

```bash
curl -fsSLO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
conda --version
```

**Linux, ARM (aarch64)**

```bash
curl -fsSLO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh
bash Miniconda3-latest-Linux-aarch64.sh
source ~/.bashrc
conda --version
```

**Windows**: use WSL2, then follow the Linux box for your chip. Every Linux
instruction on this page then applies exactly as written.

Native Windows runs everything **except atmospheric correction**: the readers,
topographic and BRDF correction, quality flags, spectral tools, resampling,
alignment and export, and the `search`, `srf`, `search-map` and `brdf` extras.
Every package those need publishes a Windows wheel or is pure Python. Install conda from
[`Miniconda3-latest-Windows-x86_64.exe`](https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe),
open **Anaconda Prompt**, and use these - the same lines as the Linux box
without the compilers, without `[atmos]`, and **without the quotes**, which
Anaconda Prompt passes through to pip instead of removing:

```bat
conda create -n hyperproc python=3.12
conda activate hyperproc

pip install hyperproc
pip install hyperproc[search]
pip install hyperproc[srf]
pip install hyperproc[search-map]
pip install hyperproc[brdf]
pip install hyperproc[notebooks]
```

`[atmos]` is the one that will not work, and the reason is not packaging.
ISOFIT installs, but the radiative-transfer engines are compiled from source
on the machine: 6S is Fortran and needs `gfortran` and `make`, libRadtran is C
and Fortran against GSL and runs `./configure`. None of that is part of a
Windows toolchain, and the engines have no Windows build - not even for the
default engine, since sRTMnet compiles 6S underneath. WSL2 is the way to run
atmospheric correction on a Windows machine.

The installer asks you to accept the licence, choose a location, and whether
to initialise your shell. **Answer yes to the last one** - that is what makes
the `source` line work. If `conda --version` still says the command is not
found, the shell was never initialised: run `conda init zsh` on macOS or
`conda init bash` on Linux, then open a new terminal.

**Installation · Python {{ python_requires }} · Use Python 3.12 for atmospheric correction**

```bash
conda create -n hyperproc python=3.12
conda activate hyperproc
conda install -c conda-forge gfortran make gcc gsl

pip install hyperproc
pip install 'hyperproc[search]'
pip install 'hyperproc[srf]'
pip install 'hyperproc[search-map]'
pip install 'hyperproc[brdf]'
pip install 'hyperproc[atmos]'
pip install 'hyperproc[notebooks]'

hyperproc-atmos-setup
hyperproc-atmos-setup --examples
hyperproc-atmos-setup --engine LibRadTran
hyperproc-atmos-setup --check
```

That is the whole installation. The `conda install` line supplies the
compilers the atmospheric engines are built from, which pip cannot; everything
else `pip install hyperproc` needs, it installs itself.

| Extra | Adds |
|---|---|
| *(none)* | readers, correction, export |
| `search` | archive search and download |
| `srf` | published Sentinel-2 and Landsat response functions |
| `search-map` | interactive notebook maps (ipyleaflet) |
| `brdf` | Earth Engine for satellite BRDF |
| `atmos` | ISOFIT atmospheric correction |
| `notebooks` | JupyterLab, matplotlib and pandas |

The `hyperproc-atmos-setup` lines run once per machine and matter only for
`[atmos]`. The first installs the engines and data assets (~6 GB) under
`~/.isofit`; `--examples` adds ISOFIT's tutorial scenes (~340 MB),
`--engine LibRadTran` compiles libRadtran, and `--check` reports what is
already in place without downloading anything. On a shared machine, add
`--base /data/shared/isofit_assets` so every user reads one copy.

[Installation guide: environments, optional features, and setup requirements](getting-started/installation.md)

**Using hyperproc with an AI assistant**

A skill that teaches Claude Code and Codex how this package works: the sensor
and archive matrices, which grid a window indexes on each sensor and level,
the atmospheric route and its work-directory rules, and what the correction
diagnostics mean. It reports what a diagnostic found; it does not make the
scientific decisions for you.

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/FujiangJi/hyperproc.git
cd hyperproc && git sparse-checkout set skills
./skills/install.sh --claude
```

The last line takes `--claude`, `--codex` or `--both`; both install
globally, so they apply in every project on the machine. Full details, including
what to do when you already have an `AGENTS.md`:
[AI assistant skill](tools/ai-assistants.md).

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
