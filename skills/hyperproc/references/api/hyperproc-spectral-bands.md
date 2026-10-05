# hyperproc.spectral.bands

Release baseline **0.1.2**; source `hyperproc/spectral/bands.py`. Choose a callable below rather than loading every declaration.

Addressing bands by wavelength, and the runs of usable bands.

Everything spectral in this package is addressed by **wavelength**, never by
band number. That is the difference between an operation that ports across
sensors and one that quietly moves when the instrument changes: ``R860`` means
the band nearest 860 nm on whatever is in hand, and asking for a wavelength a
sensor does not cover fails loudly rather than returning the wrong band.

:func:`runs_of_good_bands` is the other half. A hyperspectral spectrum is not
one continuous signal: the water-vapour regions are unusable, and a filter, a
hull or a derivative that reaches across such a gap measures the gap. Every
function in this subpackage works inside the runs this returns.

## Declared exports

`TOLERANCE`, `band_at`, `runs_of_good_bands`, `good_bands`

## Imported aliases

- `main_var` → `hyperproc.io.main_var`

## Declared callables and classes

- [good_bands](symbols/hyperproc.spectral.bands.good_bands.md)
- [runs_of_good_bands](symbols/hyperproc.spectral.bands.runs_of_good_bands.md)
- [band_at](symbols/hyperproc.spectral.bands.band_at.md)

## Constant expressions

- [TOLERANCE](constants/hyperproc.spectral.bands.TOLERANCE.md)
