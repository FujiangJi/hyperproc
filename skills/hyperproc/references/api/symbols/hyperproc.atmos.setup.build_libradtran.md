# hyperproc.atmos.setup.build_libradtran

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def build_libradtran(path, jobs: int=8, verbose: bool=True) -> Path
```

Configure and compile an unpacked libRadtran tree.

libRadtran needs the GNU Scientific Library and netCDF at build time.
ISOFIT's own build step runs ``./configure && make`` without checking
either, and silently leaves no binary when GSL is missing. This builds
against the libraries of the running conda environment (``sys.prefix``;
``conda install -c conda-forge gsl`` supplies GSL) and verifies that
``bin/uvspec`` exists afterwards.

[Module and aliases](../hyperproc-atmos-setup.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.setup.build_libradtran --runtime`.
