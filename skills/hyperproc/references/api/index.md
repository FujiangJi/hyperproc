# Complete API reference, with live inspection

Baseline: released **hyperproc 0.1.2**, SHA256-verified wheel. Coverage: **54 modules, 445 module-level functions, 20 classes, 100 declared class members**. Internal helpers are included for completeness, not promoted to stable public APIs. Each callable has its own short document; constants have separate entries. No website article mirror is bundled.

Use the actual interpreter and absolute skill path:

```bash
python /path/to/hyperproc/scripts/api_index.py --list-modules
python /path/to/hyperproc/scripts/api_index.py --module hyperproc.atmos
python /path/to/hyperproc/scripts/api_index.py --symbol hyperproc.atmos.process --runtime
python /path/to/hyperproc/scripts/api_index.py --symbol hyperproc.io.to_geotiff --runtime --doc
```

AST mode reads installed source without importing optional submodules. Runtime mode imports only the requested target and reports its actual signature; optional dependency failures are explicit. Signatures are not truncated. Live tables/signatures follow installed code; scientific guidance remains a reviewed baseline and must be checked when behavior changes.

`hp.read` aliases `hp.open`; `hp.spectral_index` aliases `features.index`; `hp.spectral_derivative` aliases `spectral.derivative`. Quality convenience aliases map to the corresponding quality functions. `hp.search_map` is lazy; `Map` is exposed through `hp.archive.Map`, **not `hp.Map`**. Explicitly import atmospheric and correction modules (`from hyperproc.atmos import process`, `import hyperproc.correct as hc`); a fresh `import hyperproc as hp` alone does not expose `hp.atmos` or `hp.correct`.

## Modules

- [hyperproc](hyperproc.md)
- [hyperproc._ncrc](hyperproc-_ncrc.md)
- [hyperproc.align](hyperproc-align.md)
- [hyperproc.archive](hyperproc-archive.md)
- [hyperproc.archive.api](hyperproc-archive-api.md)
- [hyperproc.archive.cmr](hyperproc-archive-cmr.md)
- [hyperproc.archive.collections](hyperproc-archive-collections.md)
- [hyperproc.archive.dlr](hyperproc-archive-dlr.md)
- [hyperproc.archive.interactive](hyperproc-archive-interactive.md)
- [hyperproc.archive.neon](hyperproc-archive-neon.md)
- [hyperproc.archive.results](hyperproc-archive-results.md)
- [hyperproc.atmos](hyperproc-atmos.md)
- [hyperproc.atmos._runner](hyperproc-atmos-_runner.md)
- [hyperproc.atmos.aerosols](hyperproc-atmos-aerosols.md)
- [hyperproc.atmos.correct](hyperproc-atmos-correct.md)
- [hyperproc.atmos.dem](hyperproc-atmos-dem.md)
- [hyperproc.atmos.engines](hyperproc-atmos-engines.md)
- [hyperproc.atmos.inputs](hyperproc-atmos-inputs.md)
- [hyperproc.atmos.process](hyperproc-atmos-process.md)
- [hyperproc.atmos.setup](hyperproc-atmos-setup.md)
- [hyperproc.correct](hyperproc-correct.md)
- [hyperproc.correct.brdf](hyperproc-correct-brdf.md)
- [hyperproc.correct.cfactor](hyperproc-correct-cfactor.md)
- [hyperproc.correct.coefficients](hyperproc-correct-coefficients.md)
- [hyperproc.correct.kernels](hyperproc-correct-kernels.md)
- [hyperproc.correct.masks](hyperproc-correct-masks.md)
- [hyperproc.correct.mcd43](hyperproc-correct-mcd43.md)
- [hyperproc.correct.pipeline](hyperproc-correct-pipeline.md)
- [hyperproc.correct.topo](hyperproc-correct-topo.md)
- [hyperproc.features](hyperproc-features.md)
- [hyperproc.geometry](hyperproc-geometry.md)
- [hyperproc.grid](hyperproc-grid.md)
- [hyperproc.io](hyperproc-io.md)
- [hyperproc.quality](hyperproc-quality.md)
- [hyperproc.readers](hyperproc-readers.md)
- [hyperproc.readers._common](hyperproc-readers-_common.md)
- [hyperproc.readers.aviris](hyperproc-readers-aviris.md)
- [hyperproc.readers.desis](hyperproc-readers-desis.md)
- [hyperproc.readers.emit](hyperproc-readers-emit.md)
- [hyperproc.readers.enmap](hyperproc-readers-enmap.md)
- [hyperproc.readers.neon](hyperproc-readers-neon.md)
- [hyperproc.readers.pace](hyperproc-readers-pace.md)
- [hyperproc.readers.prisma](hyperproc-readers-prisma.md)
- [hyperproc.readers.tanager](hyperproc-readers-tanager.md)
- [hyperproc.registry](hyperproc-registry.md)
- [hyperproc.report](hyperproc-report.md)
- [hyperproc.spectral](hyperproc-spectral.md)
- [hyperproc.spectral._smoothspline](hyperproc-spectral-_smoothspline.md)
- [hyperproc.spectral.bands](hyperproc-spectral-bands.md)
- [hyperproc.spectral.continuum](hyperproc-spectral-continuum.md)
- [hyperproc.spectral.derivatives](hyperproc-spectral-derivatives.md)
- [hyperproc.spectral.resampling](hyperproc-spectral-resampling.md)
- [hyperproc.spectral.smoothing](hyperproc-spectral-smoothing.md)
- [hyperproc.spectral.srf](hyperproc-spectral-srf.md)

[Machine inventory](../provenance/api-inventory.json) and [release provenance](../provenance/release-manifest.json).
