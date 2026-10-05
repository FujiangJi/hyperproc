# hyperproc.readers.aviris._add_elevation

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _add_elevation(ds: xr.Dataset, cube: Path, variant: _Variant, granule: str) -> None
```

Attach a per-pixel DEM, orthorectifying it first if need be.

Topographic correction needs elevation, and so does any honest check of the
slope layer - which is the point: with a DEM in hand the slope convention
can be *tested* rather than assumed per instrument.

Only AVIRIS-3 delivers it already gridded (``LOC_ORT``). NG and Classic
hand over the raw sensor grid (``loc``/``ort_igm``) plus a lookup table, so
those get the same GLT treatment as AVIRIS-5's OBS.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._add_elevation --runtime`.
