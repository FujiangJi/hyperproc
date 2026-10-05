# hyperproc.atmos.engines.SixS

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

6S with a selectable aerosol model and ozone column, at instrument wavelengths.

Two things differ from ISOFIT's class. The aerosol model (line 5 of the
6S input) and, when ``ozone`` is given, the ozone column (lines 4 and 10,
atm-cm) are edited into each input file after the parent writes it. And
the look-up table is stored at the instrument's wavelengths: ISOFIT keeps
6S output on 6S's own 2.5 nm grid and lets the forward model resample,
which the analytical line does not do (it fails with an 861 x 285 shape
mismatch), so each simulation is resampled here with the instrument's
FWHM, exactly as the sRTMnet route ends up at instrument resolution.

Ray workers run ``makeSim``/``readSim`` from the pickled instance, so the
settings are read before the parent's constructor, which may already
build the table.

## Declared fields

```text
SIM_RANGE = (350.0, 2500.0)
```

## Declared members

- [__init__](hyperproc.atmos.engines.SixS.__init__.md)
- [rebuild_cmd](hyperproc.atmos.engines.SixS.rebuild_cmd.md)
- [_sim_grid](hyperproc.atmos.engines.SixS._sim_grid.md)
- [readSim](hyperproc.atmos.engines.SixS.readSim.md)

[Module](../hyperproc-atmos-engines.md).
