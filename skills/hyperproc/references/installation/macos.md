# macOS installation (Apple Silicon or Intel)

Determine actual architecture with `uname -m`. `arm64` selects Apple Silicon; `x86_64` selects Intel or a Rosetta process. Prefer a native environment for the machine and do not mix architecture-specific libraries.

Use existing compatible conda if available. Otherwise select the matching official bootstrap:

```bash
# Apple Silicon:
curl -fsSLO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
bash Miniforge3-MacOSX-arm64.sh
# Intel: replace arm64 with x86_64 in both lines.
```

After completing the installer, source its actual prefix (default shown), then create the processing environment:

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda create -n hyperproc python=3.12 pip
conda activate hyperproc
python -m pip install "hyperproc==0.1.2"
python -m pip check
```

A compatible existing Miniconda environment is equally usable. Verify `sys.executable` and `platform.machine()`; do not accidentally run the base interpreter or a notebook kernel from another architecture. The baseline pin is optional when the user explicitly targets a newer release; live checks are then mandatory for the intended APIs.

For atmospheric processing, obtain Fortran/make tools in this environment:

```bash
conda install -c conda-forge gfortran make
```

The LibRadTran route also needs a usable C compiler and GSL. macOS C tooling can come from Xcode Command Line Tools (`xcode-select --install`, if absent and authorized); install GSL in the conda environment with `conda install -c conda-forge gsl`. Run the engine-specific check and verify actual `gcc`/`gfortran`/`make`/`gsl-config` discovery. Compiler package names/binaries differ by platform; do not assume the Linux `gcc` conda recipe is universally available on macOS. Record missing tools rather than repeatedly launching a failing build.

Follow [capabilities](capabilities.md), [assets](atmos-assets.md), and [verification](verification.md). A netCDF rc final-newline issue can cause worker failures; it is one diagnostic hypothesis, not proof every macOS crash has that cause. See [troubleshooting](../operations/troubleshooting.md).

Official installers: [conda-forge download](https://conda-forge.org/download/) and [Miniforge](https://github.com/conda-forge/miniforge). This skill does not claim a fresh full macOS retrieval test.
