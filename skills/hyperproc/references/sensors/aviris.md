Published counterpart: [https://fujiangji.github.io/hyperproc/sensors/aviris/](https://fujiangji.github.io/hyperproc/sensors/aviris/).

This is a workflow reference, not permission to authenticate, download assets, accept policies, or overwrite data. Exact API defaults belong to the released API atlas.

# AVIRIS Classic, NG, 3, and 5

One variant-aware reader, `open_aviris()`, supports the AVIRIS family. Use intact provider naming and metadata; the reader infers the instrument and measurement from the delivery.

| Variant | Important implementation details |
|---|---|
| Classic | ENVI; integer radiance can require `.gain` scaling; spectral sidecars and overlapping spectrometer bands need attention |
| NG | ENVI products and associated observation/geometry information |
| AVIRIS-3 | ENVI; potentially rotated flight-aligned map grids; geometry-convention checks |
| AVIRIS-5 | NetCDF; flightlines can be delivered as multiple chunks; radiance/GLT behavior differs from older variants |

- [Open](aviris-01.md)
- [Options and cautions](aviris-02.md)
- [Next steps](aviris-03.md)
