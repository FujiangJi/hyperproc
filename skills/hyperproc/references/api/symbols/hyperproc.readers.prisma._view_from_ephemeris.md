# hyperproc.readers.prisma._view_from_ephemeris

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _view_from_ephemeris(f, ds: xr.Dataset)
```

View zenith/azimuth per pixel from the WGS-84 satellite positions in the file.

Line times are spread linearly between the product start and stop times;
the ephemeris (GPS seconds of day, 18 s ahead of UTC) is interpolated to
them; the ground point is the pixel's lat/lon at sea level (elevation
changes the angles by hundredths of a degree at 615 km).

[Module and aliases](../hyperproc-readers-prisma.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.prisma._view_from_ephemeris --runtime`.
