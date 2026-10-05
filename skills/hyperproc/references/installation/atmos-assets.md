# ISOFIT build tools, assets, and provisioning scope

First install the selected atmospheric extra into a compatible environment, then inspect without provisioning:

```bash
hyperproc-atmos-setup --check
hyperproc-atmos-setup --check --engine LibRadTran
```

Only check engines needed by the task. The default sRTMnet route needs compiled 6S plus emulator/surface assets; gfortran/make matter. LibRadTran additionally needs a usable C compiler and GSL; confirm `gsl-config` and an actual built `uvspec`, not merely unpacked source. Choose [Linux](linux.md) or [macOS](macos.md) toolchain guidance; Windows uses [WSL2](wsl2.md) for this release's build path.

**Before provisioning, show the asset base, missing components, approximate transfer volume (several GB for a typical fresh default stack), any unknown sizes, free disk and build/work allowance. Get approval for that concrete transfer unless already explicitly authorized.** Never interpret a scene-processing request as automatic permission to fetch every engine/example dataset. Inspect the existing asset base to avoid unnecessary repeated downloads.

After approval, for the selected default stack:

```bash
hyperproc-atmos-setup --base /path/to/approved/isofit_assets
hyperproc-atmos-setup --check
```

Optional LibRadTran and examples are distinct choices:

```bash
hyperproc-atmos-setup --base /path/to/approved/isofit_assets --engine LibRadTran
# Only when examples are requested and their extra transfer is approved:
hyperproc-atmos-setup --examples
```

The default base is `~/.isofit`; ISOFIT records configuration in `~/.isofit/isofit.ini`. Shared assets should be in an approved persistent location outside an ephemeral environment. Setup can fetch/build/update external state and append a missing final newline in home netCDF rc files. `--check` reports without that repair. Disclose configuration effects before applying setup to an existing shared installation.

The installed upstream metadata/commands control actual readiness. [ISOFIT's framework documentation](https://github.com/isofit/isofit) describes radiance/location/observation inputs and engines; hyperproc's wrapper adds its own setup/process constraints. Do not blindly substitute commands from a different ISOFIT major release.

Finish with engine-specific `--check`, dependency/import verification, a bounded supported product trial if provisioned and authorized, and separate source-versus-runtime-versus-scientific validation claims. Missing assets must not be silently replaced by a different engine or invented priors.
