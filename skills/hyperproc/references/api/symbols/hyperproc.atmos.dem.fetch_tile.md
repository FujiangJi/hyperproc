# hyperproc.atmos.dem.fetch_tile

Release baseline: **0.1.2**. Non-underscore declaration; verify export/usage context.

```text
def fetch_tile(lat0: int, lon0: int, resolution: int=30, verbose: bool=False) -> Path | None
```

The cached tile file, downloading it on first use; None when the tile does not exist.

[Module and aliases](../hyperproc-atmos-dem.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.dem.fetch_tile --runtime`.
