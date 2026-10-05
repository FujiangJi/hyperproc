# hyperproc.correct.coefficients

Release baseline **0.1.2**; source `hyperproc/correct/coefficients.py`. Choose a callable below rather than loading every declaration.

Coefficient files.

A correction is only as trustworthy as its coefficients, so hyperproc writes
them to JSON where they can be read, reused and audited. Design choices:

* **Keyed by wavelength** (nanometres, 4 decimals), never by band index. Band
  indices change with band subsets and mean nothing across sensors; a
  wavelength key can be aligned to any cube of the same instrument.
* **Diagnostics next to the numbers.** Every topographic C carries the fit's
  slope, intercept, r, effect size, t statistic, sample count and status; a
  BRDF fit carries its bins, samples per bin, r2 per band and bin, and the
  angular-diversity check that says whether the fit was identifiable.
* **Provenance.** Which inputs (by stem), which masks, which settings, which
  software version, when. The pairing of a coefficient file with its image is
  written *inside* the file - the failure mode where files get matched by
  directory listing order is not reproducible here.

Two containers: :class:`TopoCoefficients` (one image) and
:class:`BRDFCoefficients` (one group of images).

## Imported aliases

- `FlexFit` → `hyperproc.correct.brdf.FlexFit`

## Declared callables and classes

- [_now](symbols/hyperproc.correct.coefficients._now.md) — internal
- [provenance](symbols/hyperproc.correct.coefficients.provenance.md)
- [_jsonable](symbols/hyperproc.correct.coefficients._jsonable.md) — internal
- [_wl_key](symbols/hyperproc.correct.coefficients._wl_key.md) — internal
- [align_wavelengths](symbols/hyperproc.correct.coefficients.align_wavelengths.md)
- [load](symbols/hyperproc.correct.coefficients.load.md)
- [TopoCoefficients](symbols/hyperproc.correct.coefficients.TopoCoefficients.md)
- [BRDFCoefficients](symbols/hyperproc.correct.coefficients.BRDFCoefficients.md)

## Constant expressions

- [FORMAT](constants/hyperproc.correct.coefficients.FORMAT.md)
- [VERSION](constants/hyperproc.correct.coefficients.VERSION.md)
