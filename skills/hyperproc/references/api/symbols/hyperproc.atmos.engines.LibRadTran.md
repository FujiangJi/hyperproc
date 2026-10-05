# hyperproc.atmos.engines.LibRadTran

Release baseline **0.1.2**. Fields and declared members below come from the release source. Dataclass/inherited methods may be generated at runtime; inspect the installed class signature when constructing it.

libRadtran with a selectable Shettle haze type on top of ``aerosol_default``.

Ozone and CO2 come from the MODTRAN template ISOFIT writes (``O3STR``,
``CO2MX``); the runner edits ``O3STR`` there when ``ozone`` is given.

## Declared members

- [__init__](hyperproc.atmos.engines.LibRadTran.__init__.md)

[Module](../hyperproc-atmos-engines.md).
