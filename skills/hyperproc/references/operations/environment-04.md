## Diagnose environment failures

Confirm `sys.executable`, distribution versions, kernel interpreter, `python -m pip` target, optional capability, compiled dependency import, and platform before blaming the dataset. A package version can come from editable metadata while imported source comes from another path; if necessary inspect `hyperproc.__file__` and installed source. Linux/macOS are the documented paths; do not promise tested native Windows atmospheric builds. WSL2 may be the relevant Windows route. Avoid emitting tokens or the contents of credential/configuration files.
