# hyperproc.spectral.srf

Release baseline **0.1.2**; source `hyperproc/spectral/srf.py`. Choose a callable below rather than loading every declaration.

Spectral response functions for common instruments, fetched and cached.

Convolving a hyperspectral cube onto a broadband sensor is only as good as the
response you convolve with. For most instruments the real, measured response is
published, and this module goes and gets it::

    from hyperproc.spectral import srf
    print(srf.available())                  # what is known, and what is cached
    s2 = srf.fetch("SENTINEL2A")            # downloads once, then reads the cache
    hp.resample(ds, sensor="LANDSAT8")      # the same thing, through resample

Downloads land in ``$HYPERPROC_CACHE_DIR/srf`` as the original spreadsheet plus
a parsed ``.npz``, so the network is touched once per instrument.

Measured, or nominal
--------------------
Two kinds of entry, and the difference is recorded in ``kind`` rather than left
for you to guess:

``measured``
    A tabulated response per band, from the agency. Sentinel-2 MSI from ESA,
    Landsat TM, ETM+, OLI and OLI-2 from the USGS spectral viewer.
``nominal``
    Only published band edges, turned into centres and widths. PlanetScope is
    here because Planet publishes band ranges rather than response curves. A
    nominal entry is used with a Gaussian response, which on PACE's measured
    bands differs from the real curve by about 0.2 % in the median, so it is a
    fair approximation but it is not the instrument.

Bands whose response falls outside the source's coverage come back NaN from
:func:`hyperproc.spectral.resample`, which matters here: simulating Sentinel-2
band 10 (1375 nm cirrus) from EMIT cannot work, because that wavelength sits in
a water-vapour gap EMIT does not measure.

## Declared exports

`SOURCES`, `NOMINAL`, `ALIASES`, `available`, `fetch`, `target`, `cache_dir`, `resolve`

## Declared callables and classes

- [cache_dir](symbols/hyperproc.spectral.srf.cache_dir.md)
- [resolve](symbols/hyperproc.spectral.srf.resolve.md)
- [_load_workbook](symbols/hyperproc.spectral.srf._load_workbook.md) — internal
- [_to_nm](symbols/hyperproc.spectral.srf._to_nm.md) — internal
- [_parse_sentinel2](symbols/hyperproc.spectral.srf._parse_sentinel2.md) — internal
- [_parse_landsat](symbols/hyperproc.spectral.srf._parse_landsat.md) — internal
- [_summarise](symbols/hyperproc.spectral.srf._summarise.md) — internal
- [_download](symbols/hyperproc.spectral.srf._download.md) — internal
- [fetch](symbols/hyperproc.spectral.srf.fetch.md)
- [target](symbols/hyperproc.spectral.srf.target.md)
- [available](symbols/hyperproc.spectral.srf.available.md)

## Constant expressions

- [_S2](constants/hyperproc.spectral.srf._S2.md)
- [_USGS](constants/hyperproc.spectral.srf._USGS.md)
- [SOURCES](constants/hyperproc.spectral.srf.SOURCES.md)
- [NOMINAL](constants/hyperproc.spectral.srf.NOMINAL.md)
- [ALIASES](constants/hyperproc.spectral.srf.ALIASES.md)
- [_UA](constants/hyperproc.spectral.srf._UA.md)
- [SQRT_8LN2](constants/hyperproc.spectral.srf.SQRT_8LN2.md)
