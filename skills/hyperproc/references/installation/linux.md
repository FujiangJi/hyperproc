# Linux installation (x86_64 or aarch64)

Check `uname -m`, available conda, shell and free disk. If conda exists, skip bootstrap. Otherwise choose the architecture-specific official installer below; review the transfer/installation destination before executing it.

```bash
uname -m
# x86_64:
curl -fsSLO https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh
# For aarch64, use Miniforge3-Linux-aarch64.sh instead.
```

Use the installer's chosen prefix. For the default prefix in an existing session:

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda create -n hyperproc python=3.12 pip
conda activate hyperproc
python -m pip install "hyperproc==0.1.2"
python -m pip check
```

The pin reproduces the reviewed baseline; if the user chooses a newer release, preserve that choice and perform live API/environment checks. Do not install into conda base or system Python merely to save a step. Initializing a login shell is optional persistent configuration; sourcing the prefix script activates conda for this session without changing startup files.

For search/SRF/notebooks or other capabilities, select only needed extras in [capabilities](capabilities.md). Pip installs core Python dependencies; do not preinstall an arbitrary conflicting stack. If wheels are unavailable, investigate OS/architecture/library constraints before attempting a source-build campaign.

Atmospheric build tools are separate:

```bash
conda install -c conda-forge gfortran make
# Additional C/GSL tools for this release's LibRadTran route:
conda install -c conda-forge gcc gsl
```

These commands install tools in the selected environment; they do not fetch ISOFIT model/data assets. Follow [asset planning](atmos-assets.md), check the selected engine, and disclose multi-GB transfer before provisioning. On shared clusters, use approved environment/module/asset locations; do not assume sudo access or interactive login-shell initialization.

Official bootstrap: [Miniforge](https://github.com/conda-forge/miniforge). Environment mechanics: [conda environments](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html). Installer support/minimum OS requirements can change; verify the release for an older Linux host.
