# hyperproc.atmos.setup

Release baseline **0.1.2**; source `hyperproc/atmos/setup.py`. Choose a callable below rather than loading every declaration.

One-time environment setup and health check for :mod:`hyperproc.atmos`.

ISOFIT is a pip package, but the radiative-transfer engines it drives are not:
6S is Fortran that must be compiled on the machine, sRTMnet is a 5.5 GB set
of emulator weights, LibRadTran is a compiled C/Fortran package, and the data
and surface libraries add another ~100 MB. ISOFIT keeps all of them under one
base directory named in ``~/.isofit/isofit.ini``. On a shared machine point
every user at one base (``setup(base="/data/.../isofit_assets")``) so the
assets are fetched once.

* :func:`check` reports what is installed and what is missing. It never
  downloads anything.
* :func:`setup` fetches (and compiles) what the requested engines need, then
  runs :func:`check`.
* ``hyperproc-atmos-setup`` is the command-line form of :func:`setup`.

## Imported aliases

- `terminate_rc_file` → `hyperproc._ncrc.terminate_rc_file`
- `unterminated_rc_files` → `hyperproc._ncrc.unterminated_rc_files`

## Declared callables and classes

- [_quiet](symbols/hyperproc.atmos.setup._quiet.md) — internal
- [_isofit](symbols/hyperproc.atmos.setup._isofit.md) — internal
- [_assets_for](symbols/hyperproc.atmos.setup._assets_for.md) — internal
- [libradtran_exe](symbols/hyperproc.atmos.setup.libradtran_exe.md)
- [build_libradtran](symbols/hyperproc.atmos.setup.build_libradtran.md)
- [check](symbols/hyperproc.atmos.setup.check.md)
- [_report](symbols/hyperproc.atmos.setup._report.md) — internal
- [setup](symbols/hyperproc.atmos.setup.setup.md)
- [main](symbols/hyperproc.atmos.setup.main.md)

## Constant expressions

- [ENGINES](constants/hyperproc.atmos.setup.ENGINES.md)
- [NEEDS](constants/hyperproc.atmos.setup.NEEDS.md)
- [COMPILERS](constants/hyperproc.atmos.setup.COMPILERS.md)
- [PIP_HINT](constants/hyperproc.atmos.setup.PIP_HINT.md)
