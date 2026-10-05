# hyperproc.atmos.process.to_map_grid

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def to_map_grid(ds: xr.Dataset, source: str | Path | None=None, window: dict | None=None, like: xr.Dataset | None=None) -> xr.Dataset
```

A projected version of a corrected dataset, whatever grid it came on.

* already has a CRS (AVIRIS-3/5 L1B, EnMAP L1C, Tanager): returned as is;
* EMIT sensor grid: gathered through the granule's GLT (needs ``source``,
  the L1B file, or ``attrs["source"]`` which :func:`hyperproc.open` records);
* anything else with ``lat``/``lon`` layers (PRISMA, DESIS, PACE):
  :func:`hyperproc.georeference`, onto the grid of ``like`` when given
  (for example ASI's PRISMA L2D, so the product compares cell for cell).

[Module and aliases](../hyperproc-atmos-process.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.process.to_map_grid --runtime`.
