## External resources and scope

`HYPERPROC_CACHE_DIR` controls the default cache root (otherwise `~/.cache/hyperproc`), with DEM/SRF/MCD43 subdirectories. `nbar(cache_dir=...)` and `mcd43.fetch(out_dir=...)` have different parameter names. Scene downloads use `hp.download(..., out_dir=...)` separately. ISOFIT assets default to `~/.isofit`, with external configuration in `~/.isofit/isofit.ini`.

`hyperproc-atmos-setup --check` reports engine/assets/build availability. Setup without `--check` can install/fetch assets, compile engines, update configuration, and repair home-directory netCDF configuration final newlines. Do not run setup merely to inspect an unrelated product. sRTMnet still needs compiled 6S; `make`/Fortran tools matter. LibRadTran also needs C/GSL prerequisites.

Release 0.1.2 checks nonempty `.ncrc`, `.daprc`, and `.dodsrc` for missing final newlines. CMR warns after login; the atmospheric runner checks home/work directories unless `NCRCENV_RC` selects an explicit configuration. The explicit file remains the caller's responsibility. `--check` does not repair; setup may append a newline. Prefer a scoped repair after identifying the actual configuration and user authorization, rather than rewriting authentication settings.

Use a unique ISOFIT work directory for scene, exact region, engine, and meaningful parameter changes. A completed work directory may cause reuse. `dry_run` can prepare files and is not a read-only operation. `overwrite=True`, `redo="all"`, and `redo="line"` differ in what they rerun/replace.
