# hyperproc.readers.aviris._blank_water_bands

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _blank_water_bands(ds: xr.Dataset) -> None
```

NaN the water-vapour bands, keeping the band count.

Uses the product's own ``bbl`` when it has one; AVIRIS-3 flags 35 of 284
bands. Classic, NG and AVIRIS-5 ship no flag, so :data:`WATER_BANDS` stands
in - the windows AVIRIS-3's list marks.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._blank_water_bands --runtime`.
