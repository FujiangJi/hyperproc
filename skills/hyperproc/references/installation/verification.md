# Verify the selected environment before processing

Use the exact interpreter planned for the script/notebook:

```bash
python -c "import sys, hyperproc as hp; print(sys.executable); print(hp.__version__); print(hp.__file__)"
python -m pip check
python /path/to/hyperproc/scripts/env_report.py --capability core
python /path/to/hyperproc/scripts/sensor_table.py
python /path/to/hyperproc/scripts/api_index.py --symbol hyperproc.io.to_geotiff --runtime
```

Substitute the skill path; do not assume `scripts/` is the user's current directory. Confirm import path, version, core scientific-library imports and chosen capability. A metadata-ready report is not a compiled-library ABI test. For atmosphere, add `--capability atmos --atmos-engine sRTMnet`; for credentials, opt into `--credentials` (local availability only).

For a Jupyter workflow, install only the requested notebook extra, register/select the environment kernel where appropriate, and verify `sys.executable` inside the notebook. Kernel registration writes user/project state; do not do it merely to process a terminal script.

The bundle's offline validator can run synthetic helper/QA/index/export checks when scientific dependencies are already provisioned. It does not install packages, download scenes or retrieve atmosphere. A passing Linux synthetic test does not establish full macOS/Windows or every real sensor/engine coverage.

Before full-scale output, open the actual supported product with its required companions, inspect units/bands/geometry, choose a valid bounded window, and validate an actual small output on disk. Failures should identify the import/asset/product/phase involved. Do not repeatedly rerun a full scene while debugging a missing dependency.
