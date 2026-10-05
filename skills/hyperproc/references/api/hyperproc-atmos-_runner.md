# hyperproc.atmos._runner

Release baseline **0.1.2**; source `hyperproc/atmos/_runner.py`. Choose a callable below rather than loading every declaration.

``python -m hyperproc.atmos._runner``: ``apply_oe`` with the config adjusted.

Usage::

    python -m hyperproc.atmos._runner [--engine 6s --aerosol-model maritime --ozone 0.28]
        [--set forward_model/atmosphere/statevector/AOT550/prior_sigma=1.0]
        -- <every apply_oe argument, --emulator_base included>

Two things it can change that ``apply_oe`` does not expose: which engine
fills the look-up table, and any single value of the ISOFIT configuration
(``--set``), such as the aerosol prior.

``apply_oe`` is driven exactly as for sRTMnet (the ``--emulator_base`` keeps it
on that code path, which also sets the one-component forward model). Two hooks
change what runs underneath:

* ``template_construction.build_config`` is wrapped so that, right after
  ``apply_oe`` writes a config (the water-vapour presolve and the full one),
  the sRTMnet engine block is replaced by a 6S or libRadtran block. Geometry
  and date for 6S come from the MODTRAN template ``apply_oe`` also writes,
  the same way ISOFIT's own sRTMnet driver derives its 6S runs.
* ISOFIT's engine registry maps ``6s`` and ``LibRadTran`` to the hyperproc
  subclasses with the aerosol model exposed (:mod:`hyperproc.atmos.engines`).

Everything downstream (superpixel inversions, analytical line) is unchanged
and reads the swapped config.

## Declared callables and classes

- [libradtran_dir](symbols/hyperproc.atmos._runner.libradtran_dir.md) — internal
- [apply_overrides](symbols/hyperproc.atmos._runner.apply_overrides.md) — internal
- [rewrite_config](symbols/hyperproc.atmos._runner.rewrite_config.md) — internal
- [install](symbols/hyperproc.atmos._runner.install.md) — internal
- [main](symbols/hyperproc.atmos._runner.main.md) — internal
