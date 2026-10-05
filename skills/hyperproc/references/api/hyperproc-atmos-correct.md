# hyperproc.atmos.correct

Release baseline **0.1.2**; source `hyperproc/atmos/correct.py`. Choose a callable below rather than loading every declaration.

Run ISOFIT's ``apply_oe`` on a hyperproc L1B dataset and read the result back.

The route is the one JPL runs operationally for EMIT, AVIRIS-3 and AVIRIS-5:
``isofit apply_oe`` with the sRTMnet emulator, a water-vapour presolve, SLIC
superpixels and the analytical-line extrapolation to every pixel. Nothing is
reimplemented here; this module writes the inputs (:mod:`hyperproc.atmos.inputs`),
chooses the few parameters that depend on the scene, launches the ISOFIT
command in a subprocess, and turns ``output/<fid>_rfl`` and friends into a
hyperproc dataset with ``level = "L2A"`` and ``stem = <stem>_ac``.

What is decided automatically, and how
--------------------------------------
* **Look-up-table axes**: ``apply_oe`` reads the spans of view zenith, sun
  zenith and relative azimuth from the obs file and adds an axis only where a
  span exceeds its threshold; elevation and water vapour come from the loc
  file and the presolve. Nothing to set.
* **Atmosphere profile** (``atmosphere="auto"``): :func:`atmosphere_for` picks
  the MODTRAN/6S class from the mean latitude and the month. The winter
  classes cap the retrievable water vapour hard (MIDLAT_WINTER at 1.37 g/cm²
  at sea level), so winter is only chosen in the core winter months
  (Nov-Feb north, May-Aug south); pass a class name to override.
* **Aerosol model**: sRTMnet is trained on one continental aerosol, so only
  ``"continental"`` is valid on it. ``engine="6s"`` and ``engine="LibRadTran"``
  keep the whole ``apply_oe`` orchestration and only change the engine that
  fills the look-up table (through :mod:`hyperproc.atmos._runner`), so they
  accept the models in :data:`hyperproc.atmos.aerosols.AEROSOLS` and cost about
  the same as sRTMnet for the same scene.

## Imported aliases

- `rc_warning` → `hyperproc._ncrc.rc_warning`
- `unterminated_rc_files` → `hyperproc._ncrc.unterminated_rc_files`
- `AEROSOLS` → `hyperproc.atmos.aerosols.AEROSOLS`
- `FILL` → `hyperproc.atmos.inputs.FILL`
- `Inputs` → `hyperproc.atmos.inputs.Inputs`
- `prepare_inputs` → `hyperproc.atmos.inputs.prepare_inputs`

## Declared callables and classes

- [atmosphere_for](symbols/hyperproc.atmos.correct.atmosphere_for.md)
- [_env](symbols/hyperproc.atmos.correct._env.md) — internal
- [emulator_path](symbols/hyperproc.atmos.correct.emulator_path.md)
- [surface_recipe](symbols/hyperproc.atmos.correct.surface_recipe.md)
- [_cache_dir](symbols/hyperproc.atmos.correct._cache_dir.md) — internal
- [_surface_key](symbols/hyperproc.atmos.correct._surface_key.md) — internal
- [resolve_surface](symbols/hyperproc.atmos.correct.resolve_surface.md)
- [build_command](symbols/hyperproc.atmos.correct.build_command.md)
- [atm_terms](symbols/hyperproc.atmos.correct.atm_terms.md)
- [segment_count](symbols/hyperproc.atmos.correct.segment_count.md)
- [neighbor_cap](symbols/hyperproc.atmos.correct.neighbor_cap.md)
- [resolve_neighbors](symbols/hyperproc.atmos.correct.resolve_neighbors.md)
- [_clean_partial](symbols/hyperproc.atmos.correct._clean_partial.md) — internal
- [run_record](symbols/hyperproc.atmos.correct.run_record.md)
- [settings_of](symbols/hyperproc.atmos.correct.settings_of.md)
- [is_complete](symbols/hyperproc.atmos.correct.is_complete.md)
- [_tail](symbols/hyperproc.atmos.correct._tail.md) — internal
- [run_isofit](symbols/hyperproc.atmos.correct.run_isofit.md)
- [_hdr](symbols/hyperproc.atmos.correct._hdr.md) — internal
- [_hdr_list](symbols/hyperproc.atmos.correct._hdr_list.md) — internal
- [_open_bil](symbols/hyperproc.atmos.correct._open_bil.md) — internal
- [read_outputs](symbols/hyperproc.atmos.correct.read_outputs.md)
- [redo_line](symbols/hyperproc.atmos.correct.redo_line.md)
- [correct](symbols/hyperproc.atmos.correct.correct.md)
- [_window](symbols/hyperproc.atmos.correct._window.md) — internal

## Constant expressions

- [ENGINES](constants/hyperproc.atmos.correct.ENGINES.md)
- [ATMOSPHERES](constants/hyperproc.atmos.correct.ATMOSPHERES.md)
- [DEFAULT_SURFACE](constants/hyperproc.atmos.correct.DEFAULT_SURFACE.md)
- [LINES](constants/hyperproc.atmos.correct.LINES.md)
- [ATM_NEIGHBORS](constants/hyperproc.atmos.correct.ATM_NEIGHBORS.md)
- [_SETTING_FLAGS](constants/hyperproc.atmos.correct._SETTING_FLAGS.md)
- [_SETTING_SWITCHES](constants/hyperproc.atmos.correct._SETTING_SWITCHES.md)
