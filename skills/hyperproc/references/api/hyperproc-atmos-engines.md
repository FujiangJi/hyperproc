# hyperproc.atmos.engines

Release baseline **0.1.2**; source `hyperproc/atmos/engines.py`. Choose a callable below rather than loading every declaration.

6S and libRadtran look-up-table engines with the aerosol model exposed.

ISOFIT ships both engines but fixes their aerosol: the 6S input template writes
model 1 (continental) with 0.30 atm-cm ozone, and the libRadtran template uses
``aerosol_default`` (rural). ``apply_oe`` cannot pick them at all; it only
writes an sRTMnet or MODTRAN engine block. hyperproc keeps ``apply_oe``'s
orchestration and swaps the engine block after it is written
(:mod:`hyperproc.atmos._runner`); the subclasses here read their settings from
a small JSON file beside the look-up table, written by the runner, so the
settings travel to the Ray workers inside the pickled engine instance.

Importing this module imports ISOFIT's engines (and through them torch), so
:mod:`hyperproc.atmos.correct` does not import it; only the runner does.

## Imported aliases

- `LRT_AEROSOL` → `hyperproc.atmos.aerosols.LRT_AEROSOL`
- `SIXS_AEROSOL` → `hyperproc.atmos.aerosols.SIXS_AEROSOL`

## Declared callables and classes

- [read_settings](symbols/hyperproc.atmos.engines.read_settings.md)
- [write_settings](symbols/hyperproc.atmos.engines.write_settings.md)
- [register](symbols/hyperproc.atmos.engines.register.md)
- [SixS](symbols/hyperproc.atmos.engines.SixS.md)
- [LibRadTran](symbols/hyperproc.atmos.engines.LibRadTran.md)

## Constant expressions

- [SIDECAR](constants/hyperproc.atmos.engines.SIDECAR.md)
