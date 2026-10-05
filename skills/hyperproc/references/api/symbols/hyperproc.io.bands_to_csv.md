# hyperproc.io.bands_to_csv

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def bands_to_csv(ds: xr.Dataset, path: str | Path) -> Path
```

Write the band table: ``wavelength``, ``fwhm``, ``good_band``.

One row per band, in the same order as the GeoTIFF from :func:`to_geotiff`,
so row *N* is band *N* in the raster. That holds after ``wl_range``
subsetting too, since both are written from the same dataset.

Args:
    ds: dataset from :func:`hyperproc.open`.
    path: output ``.csv``, or a **directory**, in which case the file is
        named ``<granule>_bands.csv``.

Returns:
    The path written.

Note:
    ``good_band`` is ``True``/``False`` from the sensor's own flag. EMIT
    ships it on L2A only, so on an L1B granule the column is written empty
    rather than guessed.

[Module and aliases](../hyperproc-io.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.io.bands_to_csv --runtime`.
