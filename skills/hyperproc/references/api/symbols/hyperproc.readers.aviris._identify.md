# hyperproc.readers.aviris._identify

Release baseline: **0.1.2**. Internal implementation symbol; prefer exported APIs.

```text
def _identify(path: Path) -> tuple[_Variant, str]
```

Work out the instrument and granule id from a path.

Checks the path's own name first, then walks up - a bare directory such as
``ang20220224t210144_rfl_v2aa1/`` names the granule even though the files
inside repeat it.

[Module and aliases](../hyperproc-readers-aviris.md). For another installed version, use `scripts/api_index.py --symbol hyperproc.readers.aviris._identify --runtime`.
