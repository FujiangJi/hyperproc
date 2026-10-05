## All-module coverage and visibility

The atlas includes 54 modules with 445 module-level function declarations and 20 class declarations (465 top-level function/class objects together). There are 100 explicitly declared class methods/properties, of which 68 names are non-underscore; one is in an internal module. This differs from counting convenience aliases or inherited/dataclass-generated methods.

Every module reference lists declared exports, imported/re-exported names, constants as source expressions, functions/signatures/docstrings, and class fields/methods. The JSON inventory records visibility and source lines/hashes. Namespace imports and lazy aliases mean a callable may be accessible through several paths. Prefer `hp.*`, `hp.archive`, `hp.spectral`, `hp.quality`, `hyperproc.correct`, and `hyperproc.atmos` exported names where suitable. Direct reader modules are valid when sensor-specific options are required. Internal `_common`, `_runner`, `_ncrc`, `_smoothspline`, and underscore functions support diagnostics/source analysis; do not treat them as guaranteed public contracts.

The atlas is intentionally exhaustive at the user's request. It is not intended to be read into an agent's context all at once. Route by module, then locate the exact callable and relevant constants. No need to read every sensor before computing one EMIT index.
