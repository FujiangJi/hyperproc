# hyperproc.atmos.process._open_for_ac

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _open_for_ac(path: Path) -> xr.Dataset
```

Open a granule the way the retrieval wants it.

EMIT is opened on its sensor grid (``ortho=False``): that is where the
per-pixel geometry lives and where JPL runs the retrieval; the GLT puts the
result on the map grid afterwards. Every other reader is opened with its
defaults: the AVIRIS-5 reader also has an ``ortho`` switch, but its sensor
grid carries no geolocation, so the correction runs on the ORT grid there.

[Module and aliases](../hyperproc-atmos-process.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.atmos.process._open_for_ac --runtime`.
