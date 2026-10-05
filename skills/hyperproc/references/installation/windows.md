# Native Windows installation

For core reading/QA/spectral/airborne corrections/alignment/export and applicable search/map/SRF/Earth Engine extras, a native Windows environment is a reasonable route. Availability and successful import of each compiled dependency must still be checked; declared portability is not a complete Windows test matrix.

Install an architecture-compatible conda distribution only if one is not already available. For x86_64, use the [official Miniforge Windows installer](https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe), then open its prompt. Do not replace another Python or modify system PATH blindly.

In that prompt:

```bat
conda create -n hyperproc python=3.12 pip
conda activate hyperproc
python -m pip install "hyperproc==0.1.2"
python -m pip install "hyperproc[search,srf]==0.1.2"
python -m pip check
python -c "import hyperproc as hp; print(hp.__version__); print(hp.__file__)"
```

The optional-extra line is only needed for search/SRF. **Use double quotes** in cmd.exe/PowerShell; single quotes are not interchangeable shell syntax in cmd.exe. Both the interpreter and notebook kernel must belong to the chosen environment. Preserve paths using `pathlib` and proper quoting when spaces are present.

This hyperproc baseline's atmospheric provisioning invokes Unix-oriented Fortran/C/configure build paths. Use [WSL2](wsl2.md) for that workflow. Do not claim ISOFIT or 6S can never support Windows: upstream versions/tools can offer other mechanisms, but they are not proof this hyperproc setup path is validated natively. WSL2 is the practical documented route here.

Windows ARM needs an explicitly supported environment architecture/dependency combination; an x86_64 installer is not automatically native ARM support. Verify the appropriate distribution or use a suitable supported Linux/WSL architecture.

Run [verification](verification.md) before processing, and a small raster round trip before trusting full output. This bundle did not execute native Windows installation or scientific processing.

Official platform installer guidance: [Miniforge README](https://github.com/conda-forge/miniforge). Generic Python virtual environments are covered in [venv](venv.md).
