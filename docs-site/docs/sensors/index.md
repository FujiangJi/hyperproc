# Sensor and product support

This matrix describes implemented reader routes in the **local code**, not support for every product a mission distributes. Band counts, resolutions, and processing versions can vary; use scene metadata rather than hard-coded nominal values.

| Sensor | Supported products | Measurement / grid | Guide |
|---|---|---|---|
| AVIRIS Classic, NG, 3, 5 | L1B, L2A | Radiance / reflectance; variant-specific ENVI or NetCDF grids | [AVIRIS](aviris.md) |
| NEON AOP | DP1.30006.001 (`L1`) | Surface reflectance flightlines | [NEON](neon.md) |
| EMIT | L1B RAD, L2A RFL | Radiance / reflectance; optional GLT mapping | [EMIT](emit.md) |
| PRISMA | L1, L2B, L2C, L2D | At-sensor radiance, surface radiance, swath/mapped reflectance | [PRISMA](prisma.md) |
| EnMAP | L1B, L1C, L2A | Separate detector radiance at L1B; mapped radiance/reflectance later | [EnMAP](enmap.md) |
| DESIS | L1B, L1C, L2A | VNIR radiance / reflectance | [DESIS](desis.md) |
| PACE OCI | L1B, L2 SFREFL | TOA reflectance / surface reflectance; swath | [PACE](pace.md) |
| Tanager | Orthorectified HDF5 L1B, L2A | Radiance / surface reflectance | [Tanager](tanager.md) |

Reader support is broader than search coverage: use [data access](../getting-started/data-access.md) for the archive collection matrix and [search and download](../workflows/search.md) to acquire a scene.

## Not implemented in this snapshot

- NEON DP3 mosaics: registry entry exists, reader not implemented.
- HISUI, GF-5/AHSI, Hyperion, and other absent readers: no implemented route.
- Generic PACE ocean-colour products: not covered by the SFREFL reader simply because the filename is NetCDF.
- Generic reopening of exported hyperproc products: use a suitable raster reader and restore the required metadata.

## Support is multidimensional

“Reader implemented” does not mean “all correction stages validated.” Consider file ingestion, geolocation, geometry availability, radiometric interpretation, atmospheric-route eligibility, quality coverage, and output validation separately. The [tutorial library](../tutorials/index.md) identifies which notebooks actually contain saved outputs.
