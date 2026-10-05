# hyperproc.atmos.dem

Release baseline **0.1.2**; source `hyperproc/atmos/dem.py`. Choose a callable below rather than loading every declaration.

Surface elevation for products that ship none, from the Copernicus DEM.

ISOFIT needs a height for every pixel (it sets the pressure altitude of the
look-up table). EMIT, PACE and the AVIRIS products carry one; DESIS, EnMAP,
Tanager and PRISMA do not. This module samples the Copernicus DEM GLO-30
(30 m, TanDEM-X, heights above the EGM2008 geoid, global except a handful of
countries that are only released at 90 m) from its public cloud-optimised
GeoTIFF tiles on AWS, one 1 x 1 degree tile at a time, and keeps the tiles
under ``$HYPERPROC_CACHE_DIR/dem`` so a region is fetched once.

Heights are above the EGM2008 geoid, which is what a pressure altitude
wants; the JPL products (EMIT, AVIRIS) carry ellipsoidal heights instead, so
the two differ by the local geoid undulation (about 36 m on the EMIT test
granule off California), which changes the surface pressure by under 0.5 %.

Tiles that do not exist (open ocean, or the excluded countries at 30 m) fall
back to GLO-90 and then to sea level. Scenes that would need more than
``MAX_TILES_30`` tiles (a PACE granule spans 20 degrees) are sampled from
GLO-90 outright; at kilometre pixels that loses nothing.

## Declared callables and classes

- [cache_dir](symbols/hyperproc.atmos.dem.cache_dir.md)
- [tile_id](symbols/hyperproc.atmos.dem.tile_id.md)
- [tile_url](symbols/hyperproc.atmos.dem.tile_url.md)
- [fetch_tile](symbols/hyperproc.atmos.dem.fetch_tile.md)
- [_read_tile](symbols/hyperproc.atmos.dem._read_tile.md) — internal
- [sample](symbols/hyperproc.atmos.dem.sample.md)
- [add_elevation](symbols/hyperproc.atmos.dem.add_elevation.md)

## Constant expressions

- [SOURCES](constants/hyperproc.atmos.dem.SOURCES.md)
- [MAX_TILES_30](constants/hyperproc.atmos.dem.MAX_TILES_30.md)
