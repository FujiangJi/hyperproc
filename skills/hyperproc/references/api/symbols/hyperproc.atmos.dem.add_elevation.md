# hyperproc.atmos.dem.add_elevation

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def add_elevation(ds, resolution: int=30, name: str='elev', overwrite: bool=False, verbose: bool=True)
```

Attach a DEM-sampled ``elev (y, x)`` layer to a dataset that has none.

Uses the dataset's ``lat``/``lon`` layers, or derives them from the map
grid when the dataset is projected. Returns the dataset (modified in place).

[Module and aliases](../hyperproc-atmos-dem.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.dem.add_elevation --runtime`.
