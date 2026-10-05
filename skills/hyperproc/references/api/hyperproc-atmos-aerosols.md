# hyperproc.atmos.aerosols

Release baseline **0.1.2**; source `hyperproc/atmos/aerosols.py`. Choose a callable below rather than loading every declaration.

Aerosol models each look-up-table engine can use.

sRTMnet is trained on one aerosol (continental) and cannot vary it. 6S selects
one of its built-in models by number; libRadtran starts from ``aerosol_default``
(Shettle rural boundary layer, background above 2 km) and can switch the
boundary-layer type to another Shettle haze. The keys below are what
``correct(aerosol_model=...)`` accepts.

## Declared callables and classes


## Constant expressions

- [SIXS_AEROSOL](constants/hyperproc.atmos.aerosols.SIXS_AEROSOL.md)
- [LRT_AEROSOL](constants/hyperproc.atmos.aerosols.LRT_AEROSOL.md)
- [AEROSOLS](constants/hyperproc.atmos.aerosols.AEROSOLS.md)
