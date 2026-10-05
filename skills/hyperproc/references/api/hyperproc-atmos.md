# hyperproc.atmos

Release baseline **0.1.2**; source `hyperproc/atmos/__init__.py`. Choose a callable below rather than loading every declaration.

Atmospheric correction through ISOFIT.

``hyperproc.atmos`` turns any hyperproc L1B radiance dataset into the inputs
ISOFIT needs, runs ISOFIT's ``apply_oe`` with a chosen look-up-table engine
(``"sRTMnet"``, ``"6s"`` or ``"LibRadTran"``) and reads the surface
reflectance back as a hyperproc dataset, so the result flows straight into
:mod:`hyperproc.correct` and :func:`hyperproc.to_geotiff`.

Step by step::

    import hyperproc as hp
    from hyperproc.atmos import check, prepare_inputs, build_command, correct, read_outputs

    check()                                   # ISOFIT, engines and assets in place?
    ds = hp.open("EMIT_L1B_RAD_....nc", ortho=False)
    inputs = prepare_inputs(ds, "work/emit")  # _rdn/_loc/_obs under work/emit/input
    build_command(inputs, workers=24)         # the apply_oe command that will run
    rfl = correct(ds, "work/emit", workers=24)  # runs it, returns the L2A dataset
    rfl6 = correct(ds, "work/emit_6s", engine="6s", aerosol_model="maritime")  # same pipeline, 6S table
    rfl = read_outputs("work/emit", template=ds)  # later, without rerunning
    process("EMIT_L1B_RAD_....nc", "products/")   # all of the above + GLT ortho -> <stem>_ac.tif

ISOFIT is an optional dependency (``pip install hyperproc[atmos]``) and needs
radiative-transfer engines and data assets that no wheel can carry: run
``hyperproc-atmos-setup`` (or :func:`hyperproc.atmos.setup.setup`) once per
machine, and :func:`hyperproc.atmos.setup.check` any time to see what is in
place.

## Declared exports

`check`, `setup`, `SENSORS`, `Inputs`, `names_for`, `prepare_inputs`, `ATMOSPHERES`, `ENGINES`, `atmosphere_for`, `build_command`, `correct`, `read_outputs`, `run_isofit`, `process`, `to_map_grid`, `dem`

## Imported aliases

- `check` → `hyperproc.atmos.setup.check`
- `setup` → `hyperproc.atmos.setup.setup`
- `SENSORS` → `hyperproc.atmos.inputs.SENSORS`
- `Inputs` → `hyperproc.atmos.inputs.Inputs`
- `names_for` → `hyperproc.atmos.inputs.names_for`
- `prepare_inputs` → `hyperproc.atmos.inputs.prepare_inputs`
- `ATMOSPHERES` → `hyperproc.atmos.correct.ATMOSPHERES`
- `ENGINES` → `hyperproc.atmos.correct.ENGINES`
- `atmosphere_for` → `hyperproc.atmos.correct.atmosphere_for`
- `build_command` → `hyperproc.atmos.correct.build_command`
- `correct` → `hyperproc.atmos.correct.correct`
- `read_outputs` → `hyperproc.atmos.correct.read_outputs`
- `run_isofit` → `hyperproc.atmos.correct.run_isofit`
- `process` → `hyperproc.atmos.process.process`
- `to_map_grid` → `hyperproc.atmos.process.to_map_grid`
- `dem` → `hyperproc.atmos.dem`

## Declared callables and classes

