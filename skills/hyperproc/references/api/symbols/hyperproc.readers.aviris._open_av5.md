# hyperproc.readers.aviris._open_av5

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _open_av5(cube: Path, granule: str, wl_range, uncertainty, chunks, fill=None, ortho=True) -> xr.Dataset
```

AVIRIS-5 ships CF-1.6 NetCDF, but its two levels are not on the same grid.

L2A reflectance (``*_RFL_ORT.nc``) is already orthorectified - 2009 x 3605
here, with ``easting``/``northing`` at the file root. L1B radiance
(``*_L1B_RDN_*_RDN.nc``) is **not**: it is the raw 2000 x 1239 sensor grid
with a lookup table alongside it, exactly like the OBS file. So the reader
applies that GLT to put radiance on the same map grid as reflectance, which
is what makes the two levels comparable pixel for pixel.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._open_av5 --runtime`.
