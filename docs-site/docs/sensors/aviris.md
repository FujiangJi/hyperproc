# AVIRIS Classic, NG, 3, and 5

One variant-aware reader, `open_aviris()`, supports the AVIRIS family. Use intact provider naming and metadata; the reader infers the instrument and measurement from the delivery.

| Variant | Important implementation details |
|---|---|
| Classic | ENVI; integer radiance can require `.gain` scaling; spectral sidecars and overlapping spectrometer bands need attention |
| NG | ENVI products and associated observation/geometry information |
| AVIRIS-3 | ENVI; potentially rotated flight-aligned map grids; geometry-convention checks |
| AVIRIS-5 | NetCDF; flightlines can be delivered as multiple chunks; radiance/GLT behavior differs from older variants |

## Open

```python
import hyperproc as hp
ds = hp.open("/path/to/AV320231005t181518_L2A_OE_product_RFL_ORT")
hp.describe(ds)
print(ds.attrs.get("geometry_check"), ds.attrs.get("geometry_fixed"))
```

The path is a naming illustration: use the actual provider product. Explicit registry aliases include `AVIRIS`, `AVIRIS-CLASSIC`, `AVIRIS-NG`, `AVIRIS3`, and `AVIRIS5`; reported sensor attributes can use display names such as `AVIRIS-3`.

## Options and cautions

- `wl_range` subsets wavelengths; `sort_bands` controls spectral ordering.
- `geometry` attaches available observation/terrain information.
- `fix_geometry="auto"` checks a slope convention and repairs it when diagnosed; it is not a general correction for arbitrary metadata errors.
- `good_bands_only` uses bad-band handling specific to this reader; the current path can mask flagged values rather than remove the spectral coordinates.
- `map_coords=True` can expose two-dimensional map coordinates for rotated grids.
- `ortho=False` is meaningful only for supported variant pathways; do not assume it unprojects an already orthorectified ENVI product.
- Optional uncertainty and ancillary retrieval layers increase I/O.

For AVIRIS-5, distinguish a file chunk from a physical flightline when pooling samples and choosing overlap pairs. For all variants, use the full affine transform for spatial comparisons.

## Next steps

[Airborne correction](../workflows/airborne.md) · [AVIRIS-3 walkthrough](../tutorials/aviris3-walkthrough.md) · [Reader API and exact defaults](../api/hyperproc-readers-aviris.md)
